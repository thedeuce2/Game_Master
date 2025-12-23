from fastapi import FastAPI, Body, Path, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
import os
import uuid
import json
import asyncio

# =========================================================
# Configuration
# =========================================================
DB_FILE = "life_sim.db"
LOG_DIR = "static/logs"
os.makedirs(LOG_DIR, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False)

# =========================================================
# Models
# =========================================================
class Player(SQLModel, table=True):
    playerId: str = Field(primary_key=True)
    name: str | None = None
    location: str | None = None
    money: float = 0.0


class NPC(SQLModel, table=True):
    npcId: str = Field(primary_key=True)
    name: str
    description: str | None = None
    attitude: int = 0
    location: str | None = None


class Event(SQLModel, table=True):
    eventId: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    playerId: str | None = None
    summary: str
    detail: str | None = None
    worldDate: str | None = None
    worldTime: str | None = None
    worldLocation: str | None = None
    worldFunds: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =========================================================
# App Initialization
# =========================================================
app = FastAPI(
    title="Life Simulation Backend API",
    version="6.0",
    description="Dark, mature life-simulation backend for narrative AI Game Master."
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    os.makedirs(LOG_DIR, exist_ok=True)


def get_session():
    with Session(engine) as session:
        yield session


def now_header():
    now = datetime.now()
    return {
        "date": now.strftime("%B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "location": "Unknown",
        "funds": "$0.00"
    }


async def append_jsonl(file_path, obj):
    async with asyncio.Lock():
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# =========================================================
# System Endpoints
# =========================================================
@app.get("/api/meta/instructions")
async def get_meta_instructions():
    return {
        "version": "6.0",
        "tone": "Dark, mature, grounded realism with psychological intensity.",
        "instructions": (
            "You are the Game Master of a dark life simulation. Maintain player autonomy, "
            "distinct NPC individuality, and emotionally truthful storytelling. "
            "The world is gritty, realistic, and continuous."
        ),
    }


@app.get("/api/meta/directives")
async def get_storytelling_directives():
    return {
        "version": "6.0",
        "header_format": {
            "example": {
                "date": "March 14, 2025",
                "time": "10:47 PM",
                "location": "Downtown Bar",
                "funds": "$42.50",
            }
        },
        "directives": {
            "player_autonomy": "Never speak or act for the player.",
            "continuity": "Review story history before every continuation.",
            "tone": "Dark realism. No omniscience. No sanitization."
        },
    }


@app.get("/api/state/scene")
async def get_scene_state():
    header = now_header()
    return header


@app.post("/api/state/advance-time")
async def advance_time(hours: int = Body(...)):
    # In this minimal build, time is symbolic
    header = now_header()
    return {"status": "ok", "scene": header}


# =========================================================
# Player Endpoints
# =========================================================
@app.get("/api/player/{playerId}")
async def get_player(playerId: str = Path(...)):
    with Session(engine) as session:
        player = session.get(Player, playerId)
        if not player:
            player = Player(playerId=playerId)
            session.add(player)
            session.commit()
        return player


@app.patch("/api/player/{playerId}")
async def update_player(playerId: str, payload: dict = Body(...)):
    with Session(engine) as session:
        player = session.get(Player, playerId)
        if not player:
            player = Player(playerId=playerId)
        for k, v in payload.items():
            setattr(player, k, v)
        session.add(player)
        session.commit()
        return player


# =========================================================
# NPC Endpoints
# =========================================================
@app.post("/api/npc")
async def create_npc(name: str = Body(...), description: str | None = Body(None)):
    with Session(engine) as session:
        npc = NPC(name=name, description=description)
        session.add(npc)
        session.commit()
        return npc


@app.get("/api/npc/{npcId}")
async def get_npc(npcId: str = Path(...)):
    with Session(engine) as session:
        npc = session.get(NPC, npcId)
        if not npc:
            return {"error": "NPC not found"}
        return npc


# =========================================================
# Turn Resolution (The Core of Gameplay)
# =========================================================
@app.post("/api/turns/resolve")
async def resolve_turn(
    playerId: str = Body(...),
    summary: str = Body(...),
    detail: str | None = Body(None)
):
    header = now_header()
    event = Event(
        playerId=playerId,
        summary=summary,
        detail=detail,
        worldDate=header["date"],
        worldTime=header["time"],
        worldLocation=header["location"],
        worldFunds=header["funds"],
    )

    with Session(engine) as session:
        session.add(event)
        session.commit()

    await append_jsonl(os.path.join(LOG_DIR, "events.jsonl"), event.model_dump())

    return {"status": "applied", "eventId": event.eventId}


# =========================================================
# Logs
# =========================================================
@app.get("/api/logs/events")
async def get_events(limit: int = Query(50)):
    with Session(engine) as session:
        stmt = select(Event).order_by(Event.timestamp.desc()).limit(limit)
        events = session.exec(stmt).all()
        return {"events": [e.model_dump() for e in events]}


@app.get("/api/logs/pdf")
async def get_pdf_log():
    # Placeholder PDF endpoint (implement later if needed)
    pdf_url = f"/static/logs/log.pdf"
    return {"pdfUrl": pdf_url, "generatedAt": datetime.utcnow().isoformat() + "Z"}
