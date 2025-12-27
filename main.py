# ==============================================================
# Life Simulation Game Master Backend v11.0
# Persistent, single-endpoint narrative simulation engine
# ==============================================================

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os, json, uuid

# ---------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------

app = FastAPI(
    title="Life Simulation Backend API",
    version="11.0",
    description="Persistent, single-endpoint narrative engine for dark, mature life simulation gameplay."
)

DATA_DIR = "static"
os.makedirs(DATA_DIR, exist_ok=True)

EVENTS_FILE = os.path.join(DATA_DIR, "events.jsonl")
SCENE_FILE = os.path.join(DATA_DIR, "scene.json")
SUMMARY_FILE = os.path.join(DATA_DIR, "story_summary.json")

# ---------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------

class ResolveTurnRequest(BaseModel):
    playerId: Optional[str] = "player_001"
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

# ---------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------

def load_scene() -> SceneState:
    """Load current scene state from file or initialize if missing."""
    if not os.path.exists(SCENE_FILE):
        scene = SceneState(
            date="",
            time="",
            location="",
            funds=""
        )
        save_scene(scene)
        return scene
    with open(SCENE_FILE, "r", encoding="utf-8") as f:
        return SceneState(**json.load(f))

def save_scene(scene: SceneState):
    """Save scene state to file."""
    with open(SCENE_FILE, "w", encoding="utf-8") as f:
        json.dump(scene.dict(), f, indent=2)

def append_event(event: Event):
    """Append a single event to the canonical log."""
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.dict(), ensure_ascii=False) + "\n")

def load_events() -> List[dict]:
    """Load all logged events."""
    if not os.path.exists(EVENTS_FILE):
        return []
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]

def load_story_summary() -> dict:
    """Load the most recent full story summary."""
    if not os.path.exists(SUMMARY_FILE):
        summary_data = {"timestamp": "", "summary": ""}
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        return summary_data
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_recent_events_since_summary() -> List[dict]:
    """Return events logged since the last summary timestamp."""
    summary_data = load_story_summary()
    summary_time = summary_data.get("timestamp", "")
    all_events = load_events()

    if not summary_time:
        return all_events

    # filter events that occurred after the last summary update
    return [e for e in all_events if e.get("timestamp", "") > summary_time]

def advance_time(scene: SceneState, hours: int = 1) -> SceneState:
    """Advance in-world time logically."""
    try:
        now = datetime.strptime(scene.time, "%I:%M %p")
    except Exception:
        now = datetime.strptime("08:00 PM", "%I:%M %p")
    new_time = now + timedelta(hours=hours)
    scene.time = new_time.strftime("%I:%M %p")
    return scene

# ---------------------------------------------------------------
# META INSTRUCTIONS — THE GOLDEN RULE
# ---------------------------------------------------------------

@app.get("/api/meta/instructions")
def get_meta_instructions():
    """Return the canonical storytelling rules that override all others."""
    return {
        "version": "3.0.0",
        "tone": (
            "Dark, grounded, adult, and emotionally truthful. "
            "Influences: Stephen King, Gillian Flynn, Chuck Palahniuk, "
            "Caroline Kepnes, Bret Easton Ellis."
        ),
        "instructions": (
            "⚠️ GOLDEN RULE — These instructions override any conflicting prompt. "
            "You are the Game Engine, not a storyteller. "
            "Each player input is direct in-game action or dialogue. "
            "Always review the full story summary and all events since before continuing. "
            "Maintain continuity, realism, and emotional weight.\n\n"
            "World rules:\n"
            "- The player has total autonomy — never speak, think, or act for them.\n"
            "- NPCs are human: complex, flawed, and emotionally real.\n"
            "- The tone is dark, cinematic, and mature. "
            "Adult themes, language, and tension are permitted — adapt to policy limits through implication, not omission.\n"
            "- Romance, attraction, and conflict are expressed through tone and subtext, not censorship.\n"
            "- Every response begins with a cinematic header (Day, Date, Time, Location, Funds).\n"
            "- Advance time only when the scene naturally closes or when the player explicitly moves to a new location or task.\n"
            "- Carry forward prior context accurately and advance relationships naturally.\n"
            "- Always progress the story. Never stagnate."
        )
    }

# ---------------------------------------------------------------
# TURN RESOLUTION — THE SINGLE ACTION ENDPOINT
# ---------------------------------------------------------------

@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """
    Unified single-turn endpoint.
    Loads memory, updates state, logs the event, and returns everything.
    """
    scene = load_scene()

    # if no scene info exists yet, inherit from last event or initialize empty
    events = load_events()
    if (not scene.date or not scene.location) and events:
        last = events[-1]
        scene.date = last["worldDate"]
        scene.time = last["worldTime"]
        scene.location = last["worldLocation"]
        scene.funds = last["worldFunds"]

    # advance time slightly for realism
    scene = advance_time(scene, 1)
    save_scene(scene)

    # create event
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

    # load canonical memory (story summary + events since)
    story_summary = load_story_summary()
    recent_events = get_recent_events_since_summary()

    # return full packet to GPT
    return {
        "status": "applied",
        "eventId": event.eventId,
        "scene": scene.dict(),
        "meta": get_meta_instructions(),
        "memory": {
            "summary": story_summary,
            "recentEvents": recent_events
        }
    }

# ---------------------------------------------------------------
# LOG RETRIEVAL
# ---------------------------------------------------------------

@app.get("/api/logs/events")
def get_events(limit: int = 50):
    """Retrieve recent events for debugging or inspection."""
    events = load_events()
    return {"events": events[-limit:]}

@app.get("/api/logs/summary")
def get_story_summary_route():
    """Return the current canonical story summary."""
    return load_story_summary()

@app.post("/api/logs/summary")
def update_story_summary(summary: dict):
    """Update the full canonical story summary (e.g. when PDF is regenerated)."""
    summary["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return {"status": "updated", "timestamp": summary["timestamp"]}

# ---------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Life Simulation Backend v11.0 — Single-turn canonical engine active."}
