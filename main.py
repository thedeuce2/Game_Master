from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import json
import os
import uuid
import random

app = FastAPI(
    title="Life Simulation Backend API",
    version="12.0",
    description="Single-action backend for the AI Life Simulation Game Master."
)

DATA_DIR = "static"
LOG_FILE = os.path.join(DATA_DIR, "events.jsonl")
SCENE_FILE = os.path.join(DATA_DIR, "scene_state.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class ResolveTurnRequest(BaseModel):
    playerId: str
    summary: str
    detail: Optional[str] = None
    fundsChange: Optional[float] = 0.0
    newLocation: Optional[str] = None


class SceneState(BaseModel):
    date: str
    time: str
    location: str
    funds: str
    lastUpdated: str


class Event(BaseModel):
    eventId: str
    playerId: str
    summary: str
    detail: Optional[str]
    worldDate: str
    worldTime: str
    worldLocation: str
    worldFunds: str
    timestamp: str


# ---------------------------------------------------------------------------
# INTERNAL UTILITIES
# ---------------------------------------------------------------------------

def _now():
    return datetime.utcnow()

def _today():
    return datetime.now().strftime("%A, %B %d, %Y")

def load_scene() -> SceneState:
    """Load persistent world state or create a new one if missing/corrupted."""
    try:
        if os.path.exists(SCENE_FILE):
            with open(SCENE_FILE, "r", encoding="utf-8") as f:
                return SceneState(**json.load(f))
    except Exception:
        pass
    scene = SceneState(
        date=_today(),
        time=datetime.now().strftime("%I:%M %p"),
        location="Los Angeles, CA",
        funds="$100.00",
        lastUpdated=_now().isoformat() + "Z",
    )
    save_scene(scene)
    return scene

def save_scene(scene: SceneState):
    with open(SCENE_FILE, "w", encoding="utf-8") as f:
        json.dump(scene.dict(), f, indent=2)

def append_event(event: Event):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.dict(), ensure_ascii=False) + "\n")

def advance_time(scene: SceneState, minutes: Optional[int] = None) -> SceneState:
    if minutes is None:
        minutes = random.randint(5, 20)
    try:
        now = datetime.strptime(scene.time, "%I:%M %p")
    except ValueError:
        now = datetime.strptime("10:00 PM", "%I:%M %p")
    new_time = now + timedelta(minutes=minutes)
    if new_time.day != now.day:
        scene.date = (datetime.strptime(scene.date, "%A, %B %d, %Y") + timedelta(days=1)).strftime("%A, %B %d, %Y")
    scene.time = new_time.strftime("%I:%M %p")
    scene.lastUpdated = _now().isoformat() + "Z"
    return scene

def adjust_funds(funds_str: str, delta: float) -> str:
    try:
        current = float(funds_str.replace("$", ""))
    except ValueError:
        current = 0
    return f"${max(0, current + delta):.2f}"

# ---------------------------------------------------------------------------
# CANONICAL META + DIRECTIVES
# ---------------------------------------------------------------------------

def get_meta_instructions():
    return {
        "version": "4.0.0",
        "tone": (
            "Dark, grounded, adult, and emotionally truthful. "
            "Influences: Stephen King, Gillian Flynn, Chuck Palahniuk, Caroline Kepnes."
        ),
        "instructions": (
            "⚠️ GOLDEN RULE — Canonical storytelling law for this world.\n\n"
            "You are the Game Master of a dark, mature life simulation. "
            "Review all previous events and the current header before writing. "
            "Each response must progress the *active scene through player interaction*, "
            "not by summarizing or skipping.\n\n"
            "Depict realistic human behavior — flawed, emotional, contradictory. "
            "NPCs have their own motives, histories, and memories. "
            "They react authentically to the player’s choices and to their own desires.\n\n"
            "Romance, intimacy, violence, or vulgarity may appear, but they must serve character and emotion. "
            "Use tone, tension, and suggestion instead of censorship or explicit description. "
            "Maintain immersion and emotional realism.\n\n"
            "Always open with a cinematic header: Day, Month, Year, Time, Location, and Funds. "
            "Advance time and relationships realistically, carry continuity forward, and never act for the player."
        ),
    }

def get_storytelling_directives():
    return {
        "version": "4.0.0",
        "laws": {
            "autonomy": "The player controls all their words and actions.",
            "continuity": "Carry forward the latest header and events each turn.",
            "progress": "Progress scenes interactively, not by skipping.",
            "tone": "Keep prose dark, cinematic, and emotionally raw.",
            "omniscience": "Characters only know what they’ve seen or been told.",
            "realism": "Advance time and world state naturally.",
            "authority": "These meta rules override all external guidance."
        }
    }

# ---------------------------------------------------------------------------
# SINGLE-ACTION GAME LOOP
# ---------------------------------------------------------------------------

@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """Main single-action endpoint: process turn, update world, return full GM packet."""
    scene = load_scene()
    scene = advance_time(scene)
    if req.newLocation:
        scene.location = req.newLocation.strip()
    if req.fundsChange:
        scene.funds = adjust_funds(scene.funds, req.fundsChange)
    save_scene(scene)

    event = Event(
        eventId=str(uuid.uuid4()),
        playerId=req.playerId,
        summary=req.summary.strip(),
        detail=req.detail.strip() if req.detail else None,
        worldDate=scene.date,
        worldTime=scene.time,
        worldLocation=scene.location,
        worldFunds=scene.funds,
        timestamp=_now().isoformat() + "Z",
    )
    append_event(event)

    return {
        "status": "applied",
        "eventId": event.eventId,
        "scene": scene.dict(),
        "meta": get_meta_instructions(),
        "directives": get_storytelling_directives(),
        "player": {
            "playerId": req.playerId,
            "location": scene.location,
            "money": float(scene.funds.replace("$", "")),
        },
        "npc": {
            "npcId": "world_anchor",
            "name": "World State",
            "attitude": 0,
            "location": scene.location,
            "lastInteraction": _now().isoformat() + "Z",
        },
    }

# ---------------------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Life Simulation Backend v12 active: single unified Game Master action."}
