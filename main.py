# ===========================================================================
# Life Simulation Backend API v7
# ---------------------------------------------------------------------------
# Fully persistent, Render-safe FastAPI backend for your dark, mature life sim.
# Includes database self-healing, persistent SQLite storage, and fixed /resolve.
# ===========================================================================

from fastapi import FastAPI, Body
from sqlmodel import SQLModel, Field, Session, create_engine
import os, uuid, json, asyncio, datetime, traceback
import aiofiles
from pathlib import Path

# -------------------------------------------------------------------
# App Setup
# -------------------------------------------------------------------

app = FastAPI(
    title="Life Simulation Backend API",
    version="7.0",
    description="Persistent, self-healing backend for a narrative AI Game Master."
)

# -------------------------------------------------------------------
# Persistent Storage Setup
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LOG_DIR = STATIC_DIR / "logs"
DB_PATH = STATIC_DIR / "life_sim.db"

os.makedirs(LOG_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------

class Event(SQLModel, table=True):
    eventId: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    playerId: str | None = None
    sceneId: str | None = None
    summary: str
    detail: str | None = None
    worldDate: str | None = None
    worldTime: str | None = None
    worldLocation: str | None = None
    worldFunds: str | None = None
    timestamp: str | None = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")


# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def now_header():
    now = datetime.datetime.now()
    return {
        "date": now.strftime("%B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "location": "Los Angeles, CA",
        "funds": "$0"
    }

async def append_jsonl(path: str, obj: dict):
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        await f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# -------------------------------------------------------------------
# Startup (self-healing DB)
# -------------------------------------------------------------------

@app.on_event("startup")
def startup_db():
    try:
        os.makedirs(STATIC_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        SQLModel.metadata.create_all(engine)
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"❌ Database init error: {e}")
        traceback.print_exc()

# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.get("/api/meta/instructions")
def get_meta_instructions():
    return {
        "version": "7.0",
        "tone": "Dark, grounded, psychological realism.",
        "instructions": (
            "You are the Game Master of a dark, mature life simulation. Maintain player autonomy, "
            "individual NPC motives, and emotional realism. The world continues even when unseen."
        ),
    }


@app.post("/api/turns/resolve")
async def resolve_turn(
    playerId: str = Body(...),
    summary: str = Body(...),
    detail: str | None = Body(None)
):
    try:
        header = now_header()

        event = Event(
            playerId=playerId,
            summary=summary,
            detail=detail,
            worldDate=header.get("date"),
            worldTime=header.get("time"),
            worldLocation=header.get("location"),
            worldFunds=header.get("funds"),
        )

        with Session(engine) as session:
            session.add(event)
            session.commit()
            session.refresh(event)
            event_id = str(event.eventId)

        event_log_path = LOG_DIR / "events.jsonl"
        await append_jsonl(str(event_log_path), event.model_dump())

        print(f"✅ Event logged successfully: {event_id}")
        return {"status": "applied", "eventId": event_id}

    except Exception as e:
        traceback.print_exc()
        print(f"❌ Error during resolve_turn: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/logs/events")
def get_events(limit: int = 50):
    try:
        with Session(engine) as session:
            events = session.query(Event).order_by(Event.timestamp.desc()).limit(limit).all()
            return {"events": [e.model_dump() for e in events]}
    except Exception as e:
        traceback.print_exc()
        return {"events": [], "error": str(e)}


@app.get("/api/logs/pdf")
def get_pdf_log():
    return {
        "pdfUrl": None,
        "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
    }


# -------------------------------------------------------------------
# Self-Healing DB Monitor
# -------------------------------------------------------------------

async def db_watcher():
    while True:
        if not DB_PATH.exists():
            print("⚠️ Database missing — recreating...")
            try:
                SQLModel.metadata.create_all(engine)
                print("✅ Database recreated.")
            except Exception as e:
                print(f"❌ Failed to recreate DB: {e}")
        await asyncio.sleep(300)


@app.on_event("startup")
async def launch_db_watcher():
    asyncio.create_task(db_watcher())

# -------------------------------------------------------------------
# Root
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "Life Simulation Backend v7 running."}

