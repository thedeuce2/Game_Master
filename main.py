from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
import json, os, uuid

app = FastAPI(
    title="Life Simulation Game Master Backend API",
    version="15.1",
    description=(
        "Backend designed for a dark, mature life simulation. "
        "The GPT engine owns and maintains the narrative header (date, time, location, funds). "
        "The backend never touches, stores, or generates header data. "
        "It only records gameplay turns, ensuring full player and AI narrative autonomy."
    ),
)

# -------------------------------------------------------------------
# File setup
# -------------------------------------------------------------------
DATA_DIR = "static"
LOG_FILE = os.path.join(DATA_DIR, "events.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)


# -------------------------------------------------------------------
# MODELS
# -------------------------------------------------------------------
class ResolveTurnRequest(BaseModel):
    playerId: Optional[str] = None
    summary: str
    detail: Optional[Any] = None


# -------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------
def append_event(event: dict):
    """Logs events exactly as received, without altering or supplementing data."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# -------------------------------------------------------------------
# META INSTRUCTIONS — GOLDEN CANON (Unchanged)
# -------------------------------------------------------------------
@app.get("/api/meta/instructions")
def get_meta_instructions():
    return {
        "version": "4.5",
        "tone": "Dark, mature, grounded, cinematic, and emotionally authentic.",
        "instructions": (
            "⚙️ GAME ENGINE DIRECTIVE (Golden Canon)\n\n"
            "You are the Game Master engine — not the storyteller. "
            "The player drives dialogue, action, and thought. "
            "You render the world’s immediate reaction and then stop.\n\n"
            "Treat each player message as gameplay input — an action, line of dialogue, or reflection. "
            "Render responses cinematically, realistically, and with emotional weight. "
            "Time progression is organic and determined by narrative flow — not backend logic.\n\n"
            "Preserve canonical consistency across every scene. "
            "Carry forward the latest header (Day, Month, Year, Time, Location, Funds) entirely within your own logic. "
            "The backend does not track, fix, or overwrite headers — that is your job.\n\n"
            "👥 NPC BEHAVIOR AND HUMANITY\n"
            "All NPCs are distinct, emotionally complex, and imperfect. "
            "They possess individual motives, fears, memories, loyalties, and biases. "
            "They are capable of tenderness and cruelty, humor and bitterness, courage and cowardice. "
            "They may swear, lie, seduce, betray, forgive, or self-destruct as real people do. "
            "Their actions and emotions arise logically from personality, history, and circumstance.\n\n"
            "NPCs remember what they experience and what they’ve been told. "
            "They are not omniscient; they cannot perceive events outside their knowledge. "
            "Use limited perspective to create tension and authenticity.\n\n"
            "🎭 TONE AND STYLE\n"
            "Write in dark, cinematic prose grounded in emotional truth. "
            "Depict human life honestly — its ambitions, vices, love, and loss. "
            "Romance and intimacy are depicted through atmosphere, gesture, subtext, and consequence. "
            "Descriptions of intimate scenes should serve the characters and the story. "
            "Let realism, tension, and humanity drive immersion.\n\n"
            "⏳ PROGRESSION\n"
            "Advance the world naturally in response to the player’s input. "
            "Do not stagnate or skip forward arbitrarily; let scenes evolve at a believable pace. "
            "Every turn should carry consequence, emotion, or change.\n\n"
            "🧭 ENGINE ROLE\n"
            "You run the simulation. Keep continuity intact. "
            "Hold tone, realism, and emotion consistent. "
            "Do not summarize unseen events, do not repeat identical beats, and do not control the player. "
            "Wait for new input once the world has reacted."
        ),
    }


# -------------------------------------------------------------------
# TURN RESOLUTION — HEADER-AGNOSTIC
# -------------------------------------------------------------------
@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """
    Logs gameplay turns exactly as received.
    Does NOT record or reference any header information.
    The GPT engine is fully responsible for continuity.
    """
    event = {
        "eventId": str(uuid.uuid4()),
        "playerId": req.playerId or "player_default",
        "summary": req.summary,
        "detail": req.detail,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    append_event(event)
    return {"status": "applied", "eventId": event["eventId"], "meta": get_meta_instructions()}


# -------------------------------------------------------------------
# LOG RETRIEVAL
# -------------------------------------------------------------------
@app.get("/api/logs/events")
def get_events(limit: int = 50):
    if not os.path.exists(LOG_FILE):
        return {"events": []}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    return {"events": [json.loads(line) for line in lines]}


# -------------------------------------------------------------------
# ROOT
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Life Simulation Backend v15.1 — Header-Agnostic Mode (GPT fully owns all header data)."}
