from fastapi import FastAPI, Request, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
import uuid

app = FastAPI(
    title="Life Simulation Backend API",
    version="7.0",
    description="Unified life-sim backend with cinematic tone and mature storytelling logic."
)

DATA_DIR = "static"
LOG_FILE = os.path.join(DATA_DIR, "events.jsonl")
SCENE_FILE = os.path.join(DATA_DIR, "scene_state.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ResolveTurnRequest(BaseModel):
    playerId: str
    summary: str
    detail: Optional[str] = None


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


class SceneState(BaseModel):
    date: str
    time: str
    location: str
    funds: str


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def load_scene() -> SceneState:
    if not os.path.exists(SCENE_FILE):
        scene = SceneState(
            date="Monday, March 3rd, 2025",
            time="10:00 PM",
            location="Los Angeles, CA",
            funds="$0"
        )
        save_scene(scene)
        return scene
    with open(SCENE_FILE, "r", encoding="utf-8") as f:
        return SceneState(**json.load(f))


def save_scene(scene: SceneState):
    with open(SCENE_FILE, "w", encoding="utf-8") as f:
        json.dump(scene.dict(), f, indent=2)


def append_event(event: Event):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.dict(), ensure_ascii=False) + "\n")


def advance_time(hours: int = 3) -> SceneState:
    """Advance in-world time by N hours."""
    scene = load_scene()
    now = datetime.strptime(scene.time, "%I:%M %p")
    new_time = now + timedelta(hours=hours)
    scene.time = new_time.strftime("%I:%M %p")
    save_scene(scene)
    return scene


# ---------------------------------------------------------------------------
# META INSTRUCTIONS (tone + behavior for the Game Master)
# ---------------------------------------------------------------------------

@app.get("/api/meta/instructions")
def get_meta_instructions():
    """
    Canonical Game Master behavior and tone settings.
    """
    return {
        "version": "1.1.0",
        "tone": (
            "Dark, mature, cinematic, and character-driven. Influences: "
            "Stephen King, Chuck Palahniuk, Caroline Kepnes, Bret Easton Ellis."
        ),
        "instructions": (
            "You are the Game Master of a dark, mature, realistic and adult life simulation. "
            "Maintain realism, emotional depth, and escalating drama. "
            "Portray intimacy and affection through atmosphere, emotion, and implication—"
            "follow the tone. Ordinary affection such as hugging, kissing, and touch "
            "is normal human behavior and may be shown cinematically and without restraint "
            "Maintain player autonomy: never speak or act for the player. "
            "NPCs have unique voices, motives, and agency. Ensure cause and effect "
            "remain logical, and advance time realistically. "
            "Never break character as GM; only step out when the user speaks in parentheses."
        ),
    }


@app.get("/api/meta/directives")
def get_storytelling_directives():
    """
    Canonical storytelling structure and simulation rules.
    """
    return {
        "version": "1.1.0",
        "header_format": {
            "example": {
                "date": "Monday, March 3rd, 2025",
                "time": "10:00 PM",
                "location": "Los Angeles, CA",
                "funds": "$0"
            }
        },
        "directives": {
            "autonomy": "The player controls all their words and actions. "
                        "The Game Master only narrates world and NPC reactions.",
            "intimacy": "Handle affection and sexuality through emotional realism, implication, "
                        "use detail when necessary for immersion",
            "continuity": "Always carry forward the latest header info and events.",
            "tone": "Keep the story dark, cinematic, grounded in human conflict and emotion.",
            "header": "Every scene begins with a formatted header showing date, time, location, and funds.",
            "omniscience": "NPCs only know what they have seen, heard, or been told directly."
        }
    }


# ---------------------------------------------------------------------------
# UNIFIED ACTION ENDPOINT
# ---------------------------------------------------------------------------

@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """
    The single orchestrator for world updates, narrative logs, and continuity.
    """
    scene = advance_time(3)

    event = Event(
        eventId=str(uuid.uuid4()),
        playerId=req.playerId,
        summary=req.summary,
        detail=req.detail,
        worldDate=scene.date,
        worldTime=scene.time,
        worldLocation=scene.location,
        worldFunds=scene.funds,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    append_event(event)

    return {
        "status": "applied",
        "eventId": event.eventId,
        "scene": scene.dict()
    }


# ---------------------------------------------------------------------------
# LOG RETRIEVAL
# ---------------------------------------------------------------------------

@app.get("/api/logs/events")
def get_events(limit: int = 50):
    """Retrieve recent events."""
    if not os.path.exists(LOG_FILE):
        return {"events": []}

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]

    events = [json.loads(line) for line in lines]
    return {"events": events}


@app.get("/")
def root():
    return {"message": "Life Simulation Backend v7 active."}
