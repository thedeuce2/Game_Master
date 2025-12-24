# ======================================================================
# Life Simulation Backend API v10 – Game Master Engine
# ----------------------------------------------------------------------
# Single /resolve endpoint handles:
#   • time advancement
#   • world + NPC updates
#   • canonical event logging
#   • returning meta-instructions and storytelling directives
# ======================================================================

from fastapi import FastAPI, Body
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pathlib import Path
import datetime, uuid, os, json, aiofiles, traceback

# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
app = FastAPI(title="Life Simulation GM Backend", version="10.0")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LOG_DIR = STATIC_DIR / "logs"
DB_PATH = STATIC_DIR / "life_sim.db"

os.makedirs(LOG_DIR, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------
class Player(SQLModel, table=True):
    playerId: str = Field(primary_key=True)
    name: str | None = None
    location: str | None = "Los Angeles, CA"
    money: float = 0.0

class NPC(SQLModel, table=True):
    npcId: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    attitude: float = 0.0
    location: str | None = "Los Angeles, CA"
    lastInteraction: str | None = None

class SceneState(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    date: str
    time: str
    location: str
    funds: str

class Event(SQLModel, table=True):
    eventId: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    playerId: str
    summary: str
    detail: str | None = None
    worldDate: str | None = None
    worldTime: str | None = None
    worldLocation: str | None = None
    worldFunds: str | None = None
    timestamp: str | None = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

# ----------------------------------------------------------------------
# Meta instructions (the GM "bible")
# ----------------------------------------------------------------------
META_INSTRUCTIONS = {
    "version": "1.0",
    "tone": (
        "Dark, mature, character-driven realism. "
        "Influences: Stephen King, Chuck Palahniuk, Caroline Kepnes, Bret Easton Ellis. "
        "Keep it human, grounded, psychological. Allow tension, silence, subtext."
    ),
    "instructions": (
        "You are the Game Master of a continuous, character-driven life simulation. "
        "Maintain player autonomy and realism. Never act for the player. "
        "Every response must feel like a film scene — cinematic, internal, reactive. "
        "Preserve canonical continuity, escalate emotional stakes, and never reset tone."
    ),
}

STORY_DIRECTIVES = {
    "version": "1.0",
    "laws": {
        "causality": "Every event must have a believable cause and effect.",
        "conflict": "Drama emerges from human tension, not random violence.",
        "continuity": "Always remember and carry forward previous beats.",
        "autonomy": "Never dictate player thoughts or actions.",
        "grounding": "Keep all sensations, emotions, and dialogue authentic.",
    },
}

# ----------------------------------------------------------------------
# Startup
# ----------------------------------------------------------------------
@app.on_event("startup")
def startup_db():
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(SceneState)).first():
            scene = SceneState(
                date=datetime.datetime.now().strftime("%B %d, %Y"),
                time=datetime.datetime.now().strftime("%I:%M %p"),
                location="Los Angeles, CA",
                funds="$0",
            )
            session.add(scene)
            session.commit()

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def advance_time(session: Session, hours: int = 3) -> SceneState:
    scene = session.exec(select(SceneState)).first()
    dt = datetime.datetime.strptime(scene.time, "%I:%M %p")
    new_dt = dt + datetime.timedelta(hours=hours)
    if new_dt.day != dt.day:
        next_day = datetime.datetime.strptime(scene.date, "%B %d, %Y") + datetime.timedelta(days=1)
        scene.date = next_day.strftime("%B %d, %Y")
    scene.time = new_dt.strftime("%I:%M %p")
    session.add(scene)
    session.commit()
    return scene

async def append_jsonl(obj: dict):
    path = LOG_DIR / "events.jsonl"
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        await f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ----------------------------------------------------------------------
# The single Game Master endpoint
# ----------------------------------------------------------------------
@app.post("/api/turns/resolve")
async def resolve_turn(
    playerId: str = Body(...),
    summary: str = Body(...),
    detail: str | None = Body(None)
):
    """
    One action does everything:
      • Advance time
      • Update NPCs and player state
      • Log the event
      • Return the full GM packet (scene header + meta instructions + story laws)
    """
    try:
        with Session(engine) as session:
            # Ensure player exists
            player = session.get(Player, playerId)
            if not player:
                player = Player(playerId=playerId)
                session.add(player)

            # Advance world time
            scene = advance_time(session, hours=3)

            # Log the event
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

            # Simple NPC example (future: dynamic personalities)
            npc = session.exec(select(NPC).where(NPC.location == scene.location)).first()
            if not npc:
                npc = NPC(name="Mara", attitude=0.5, location=scene.location)
                session.add(npc)
            npc.attitude = min(1.0, npc.attitude + 0.05)
            npc.lastInteraction = event.timestamp
            session.commit()

            # Write to persistent log
            await append_jsonl(event.model_dump())

            # Return the GM packet
            return {
                "status": "applied",
                "eventId": event.eventId,
                "scene": {
                    "date": scene.date,
                    "time": scene.time,
                    "location": scene.location,
                    "funds": scene.funds,
                },
                "meta": META_INSTRUCTIONS,
                "directives": STORY_DIRECTIVES,
                "player": player.model_dump(),
                "npc": npc.model_dump(),
            }

    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/")
def root():
    return {"status": "ok", "message": "Life Simulation GM Backend v10 running."}

