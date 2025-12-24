# =======================================================================
# Life Simulation Backend API v8
# -----------------------------------------------------------------------
# Single-endpoint version.  /api/turns/resolve does everything:
#   • advances time
#   • logs the event
#   • updates the world header
#   • returns the new scene snapshot
# =======================================================================

from fastapi import FastAPI, Body
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pathlib import Path
import uuid, os, datetime, json, aiofiles, asyncio, traceback

# ----------------------------------------------------------------------
# App + persistent paths
# ----------------------------------------------------------------------
app = FastAPI(title="Life Simulation Backend API", version="8.0")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LOG_DIR = STATIC_DIR / "logs"
DB_PATH = STATIC_DIR / "life_sim.db"

os.makedirs(LOG_DIR, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# ----------------------------------------------------------------------
# Database models
# ----------------------------------------------------------------------
class SceneState(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    date: str
    time: str
    location: str
    funds: str

class Event(SQLModel, table=True):
    eventId: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    playerId: str | None = None
    summary: str
    detail: str | None = None
    worldDate: str | None = None
    worldTime: str | None = None
    worldLocation: str | None = None
    worldFunds: str | None = None
    timestamp: str | None = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------
def init_scene(session: Session):
    """Ensure a scene row exists."""
    scene = session.exec(select(SceneState)).first()
    if not scene:
        scene = SceneState(
            date=datetime.datetime.now().strftime("%B %d, %Y"),
            time=datetime.datetime.now().strftime("%I:%M %p"),
            location="Los Angeles, CA",
            funds="$0"
        )
        session.add(scene)
        session.commit()
    return scene

def advance_time(session: Session, hours: int = 3):
    """Advance in-world time and update stored scene header."""
    scene = init_scene(session)
    dt = datetime.datetime.strptime(scene.time, "%I:%M %p")
    new_dt = (dt + datetime.timedelta(hours=hours))
    scene.time = new_dt.strftime("%I:%M %p")
    # Roll to next day if we wrapped around midnight
    if new_dt.hour < dt.hour:
        next_day = datetime.datetime.strptime(scene.date, "%B %d, %Y") + datetime.timedelta(days=1)
        scene.date = next_day.strftime("%B %d, %Y")
    session.add(scene)
    session.commit()
    return scene

async def append_jsonl(path: Path, obj: dict):
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        await f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ----------------------------------------------------------------------
# Startup
# ----------------------------------------------------------------------
@app.on_event("startup")
def startup_db():
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        init_scene(session)
    print("✅ Database ready at", DB_PATH)

# ----------------------------------------------------------------------
# Single orchestrator endpoint
# ----------------------------------------------------------------------
@app.post("/api/turns/resolve")
async def resolve_turn(
    playerId: str = Body(...),
    summary: str = Body(...),
    detail: str | None = Body(None)
):
    """
    The single entry point.  Each call:
      1. Advances in-world time.
      2. Logs the event.
      3. Returns the updated scene header.
    """
    try:
        with Session(engine) as session:
            scene = advance_time(session, hours=3)

            event = Event(
                playerId=playerId,
                summary=summary,
                detail=detail,
                worldDate=scene.date,
                worldTime=scene.time,
                worldLocation=scene.location,
                worldFunds=scene.funds,
            )

            session.add(event)
            session.commit()
            session.refresh(event)

            await append_jsonl(LOG_DIR / "events.jsonl", event.model_dump())

            print(f"✅ Event logged: {event.eventId}")
            return {
                "status": "applied",
                "eventId": event.eventId,
                "scene": {
                    "date": scene.date,
                    "time": scene.time,
                    "location": scene.location,
                    "funds": scene.funds,
                },
            }

    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------
# View recent events
# ----------------------------------------------------------------------
@app.get("/api/logs/events")
def get_events(limit: int = 20):
    try:
        with Session(engine) as session:
            events = session.exec(select(Event).order_by(Event.timestamp.desc()).limit(limit)).all()
            return {"events": [e.model_dump() for e in events]}
    except Exception as e:
        traceback.print_exc()
        return {"events": [], "error": str(e)}

# ----------------------------------------------------------------------
# Root check
# ----------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "Life Simulation Backend v8 running."}
