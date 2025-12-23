
# Life Simulation Backend v6
# ---------------------------------------------------------
# FastAPI + Async I/O + SQLite + Persistent World Simulation
# ---------------------------------------------------------
# Author: ChatGPT (Life Sim v6 Engine)
# Version: 6.0.0

import asyncio
import json
import os
import uuid
import random
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Body, Path, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, create_engine, Session, select
import aiofiles
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---------------------------------------------------------
# Setup
# ---------------------------------------------------------

app = FastAPI(
    title="Life Simulation Backend API",
    version="6.0.0",
    description="Async persistent world-simulation backend for dark, mature narrative systems."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
LOG_DIR = os.path.join(STATIC_DIR, "logs")
DB_PATH = os.path.join(BASE_DIR, "life_sim.db")

os.makedirs(LOG_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------------------------------------
# Database setup (SQLModel)
# ---------------------------------------------------------

class Player(SQLModel, table=True):
    playerId: str = Field(primary_key=True)
    name: str | None = None
    location: str | None = None
    money: float = 0.0

class NPC(SQLModel, table=True):
    npcId: str = Field(primary_key=True)
    name: str
    description: str | None = None
    attitude: float = 0.0
    location: str | None = None

class Event(SQLModel, table=True):
    eventId: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    playerId: str | None = None
    sceneId: str | None = None
    summary: str
    detail: str | None = None
    worldDate: str | None = None
    worldTime: str | None = None
    worldLocation: str | None = None
    worldFunds: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WorldFlag(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

async def append_jsonl(file_path: str, obj: dict):
    async with aiofiles.open(file_path, "a", encoding="utf-8") as f:
        await f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def get_session():
    return Session(engine)

def now_header():
    dt = datetime.now()
    date = dt.strftime("%B %d, %Y")
    time = dt.strftime("%I:%M %p")
    return {"date": date, "time": time}

# ---------------------------------------------------------
# System Endpoints
# ---------------------------------------------------------

@app.get("/api/meta/instructions")
async def get_meta_instructions():
    return {
        "version": "6.0.0",
        "tone": "Dark, mature, character-driven, grounded realism.",
        "instructions": (
            "You are the Game Master of a dark, mature world. "
            "Maintain player autonomy, realism, and escalating tension. "
            "All events are canonical; always precheck logic."
        ),
    }

@app.get("/api/meta/directives")
async def get_directives():
    return {
        "version": "6.0.0",
        "header_format": {
            "example": {
                "date": "October 31, 1999",
                "time": "11:59 PM",
                "location": "Desolate Highway",
                "funds": "$42.00",
            }
        },
        "directives": {
            "autonomy": "Player speech and action are always user-controlled.",
            "continuity": "Preserve canonical history across sessions.",
            "tone": "Dark realism; no omniscient narration.",
        },
    }

@app.get("/api/state/scene")
async def get_scene_state(playerId: str | None = None):
    async with aiofiles.open(os.path.join(LOG_DIR, "scene_state.json"), "r") as f:
        data = json.loads(await f.read())
    return data

@app.post("/api/state/advance-time")
async def advance_time(hours: int = Body(..., embed=True)):
    state_path = os.path.join(LOG_DIR, "scene_state.json")
    if not os.path.exists(state_path):
        scene = {"date": "January 1, 2000", "time": "12:00 AM", "location": "Unknown", "funds": "$0.00"}
    else:
        async with aiofiles.open(state_path, "r") as f:
            scene = json.loads(await f.read())
    current_dt = datetime.now() + timedelta(hours=hours)
    scene["date"] = current_dt.strftime("%B %d, %Y")
    scene["time"] = current_dt.strftime("%I:%M %p")
    async with aiofiles.open(state_path, "w") as f:
        await f.write(json.dumps(scene, indent=2))
    return {"status": "advanced", "scene": scene}

@app.get("/api/state/flags")
def get_flags():
    with get_session() as session:
        flags = session.exec(select(WorldFlag)).all()
    return {"flags": {f.key: f.value for f in flags}}

@app.post("/api/state/flags")
def set_flag(key: str = Body(...), value: str = Body(...)):
    with get_session() as session:
        flag = session.get(WorldFlag, key)
        if flag:
            flag.value = value
        else:
            flag = WorldFlag(key=key, value=value)
            session.add(flag)
        session.commit()
    return {"status": "ok", "key": key, "value": value}

# ---------------------------------------------------------
# Player and NPC Endpoints
# ---------------------------------------------------------

@app.get("/api/player/{playerId}")
def get_player(playerId: str):
    with get_session() as session:
        player = session.get(Player, playerId)
        if not player:
            player = Player(playerId=playerId, money=0.0)
            session.add(player)
            session.commit()
        return player

@app.patch("/api/player/{playerId}")
def update_player(playerId: str, payload: dict = Body(...)):
    with get_session() as session:
        player = session.get(Player, playerId)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        for k, v in payload.items():
            if hasattr(player, k):
                setattr(player, k, v)
        session.commit()
        return player

@app.post("/api/npc")
def create_npc(name: str = Body(...), description: str = Body("", embed=True)):
    with get_session() as session:
        npc = NPC(npcId=str(uuid.uuid4()), name=name, description=description)
        session.add(npc)
        session.commit()
        return npc

@app.get("/api/npc/{npcId}")
def get_npc(npcId: str):
    with get_session() as session:
        npc = session.get(NPC, npcId)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        return npc

# ---------------------------------------------------------
# Event Logging
# ---------------------------------------------------------

@app.post("/api/turns/resolve")
async def resolve_turn(playerId: str = Body(...), summary: str = Body(...), detail: str | None = Body(None)):
    header = now_header()
    event = Event(playerId=playerId, summary=summary, detail=detail,
                  worldDate=header["date"], worldTime=header["time"],
                  worldLocation="Unknown", worldFunds="$0.00")
    with get_session() as session:
        session.add(event)
        session.commit()
    await append_jsonl(os.path.join(LOG_DIR, "events.jsonl"), event.model_dump())
    return {"status": "applied", "eventId": event.eventId}

@app.get("/api/logs/events")
def get_events(limit: int = Query(50)):
    with get_session() as session:
        stmt = select(Event).order_by(Event.timestamp.desc()).limit(limit)
        events = session.exec(stmt).all()
    return {"events": [e.model_dump() for e in events]}

@app.get("/api/logs/pdf")
def get_pdf_log(request: Request):
    pdf_path = os.path.join(LOG_DIR, "log.pdf")
    with get_session() as session:
        events = session.exec(select(Event).order_by(Event.timestamp)).all()
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Life Simulation Log")
    y -= 20
    c.setFont("Helvetica", 10)
    for e in events:
        line = f"[{e.timestamp}] {e.summary}"
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(50, y, line[:110])
        y -= 14
    c.save()
    return {"pdfUrl": f"{request.base_url}static/logs/log.pdf"}

# ---------------------------------------------------------
# Startup
# ---------------------------------------------------------

@app.on_event("startup")
async def startup():
    init_db()
    scene_file = os.path.join(LOG_DIR, "scene_state.json")
    if not os.path.exists(scene_file):
        async with aiofiles.open(scene_file, "w") as f:
            await f.write(json.dumps({"date": "January 1, 2000", "time": "12:00 AM", "location": "Unknown", "funds": "$0.00"}, indent=2))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("life_sim_backend_v6:app", host="0.0.0.0", port=8000, reload=True)
