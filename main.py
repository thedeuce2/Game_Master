from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
import json, os, uuid, re

app = FastAPI(
    title="Life Simulation Game Master — Continuity Engine",
    version="18.0",
    description=(
        "A single-endpoint backend for a dark, grounded, emotionally truthful life simulation. "
        "The GPT Game Master owns all narrative logic. "
        "The backend simply logs turns and returns extended context for continuity."
    ),
)

# -------------------------------------------------------------------
# File setup
# -------------------------------------------------------------------
DATA_DIR = "static"
LOG_FILE = os.path.join(DATA_DIR, "datalog.jsonl")
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
    """Write each gameplay turn exactly as received."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def read_all_events() -> List[dict]:
    """Load all logged turns."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]

def find_related_events(all_events: List[dict], query: str, limit: int = 20) -> List[dict]:
    """
    Find older events that appear related to the player’s latest input,
    using keyword search on summary/detail fields.
    """
    query_words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 3]
    matches = []
    for event in reversed(all_events):
        text = (event.get("summary", "") + " " + str(event.get("detail", ""))).lower()
        if any(q in text for q in query_words):
            matches.append(event)
        if len(matches) >= limit:
            break
    return list(reversed(matches))

# -------------------------------------------------------------------
# SINGLE ACTION — EVERYTHING HAPPENS HERE
# -------------------------------------------------------------------
@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """Single authoritative endpoint — GPT handles all world logic."""
    event = {
        "eventId": str(uuid.uuid4()),
        "playerId": req.playerId or "player_default",
        "summary": req.summary,
        "detail": req.detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    append_event(event)
    all_events = read_all_events()
    related = find_related_events(all_events, req.summary)
    recent = all_events[-25:]  # include recent continuity window

    return {
        "status": "applied",
        "eventId": event["eventId"],
        "meta": {
            "version": "4.5",
            "tone": "Dark, mature, grounded, cinematic, and emotionally authentic.",
            "instructions": (
                "(Storytelling Reminder)\n"
                "- Read and follow all of the below instructions thoroughly, every single time.\n"
                "- Review the full story so far before continuing.\n"
                "- Always progress the story. Never stagnate.\n"
                "- Maintain realistic, human drama with proper setup and payoff.\n"
                "- Preserve canonical continuity, individuality among NPCs, and the player’s total autonomy — you never speak or act for them.\n"
                "- Write dark, gritty, emotionally truthful prose.\n"
                "- Always include a header showing Day, Month, Year, Time, Location, and Funds.\n"
                "- Characters know only what they’ve seen or been told.\n"
                "- Relationships should blossom and deteriorate naturally and realistically. Not everything always goes well, and not everyone is meant to be together.\n"
                "- This world is adult, grounded, and unfiltered. Sometimes it's even graphic. Do not shy away or dampen the intense moments.\n"
                "- NPCs will use vulgarity and be motivated by greed, sex, power at times as in real life — mature themes and dialogue are expected. Do not sanitize.\n"
                "- Carry forward prior story information accurately and advance time realistically.\n"
                "- Continue the story to include the player's prompts from your last entry. Only you are telling the story. The user is playing a game and you are the engine. \n"
                "- Do not speak or act on behalf of the user’s character unless prompted, under any circumstances.\n\n"
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
                "Romance and intimacy are depicted in prose using atmosphere, gesture, subtext, and consequence. "
                "Descriptions of intimate scenes should serve the characters and the story. "
                "Let realism, tension, and humanity drive immersion.\n\n"
                "⏳ PROGRESSION\n"
                "Advance the world naturally in response to the player’s input. "
                "Do not stagnate or skip forward arbitrarily; let scenes evolve at a believable pace. "
                "The user is not telling the story, they are giving you prompts. The story should continue from your last entry. "
                "User prompts should be implemented into the story by you before they become canonical; they are not part of the story until you make them part of the story. "
                "Every turn should carry consequence, emotion, or change.\n\n"
                "🧭 ENGINE ROLE\n"
                "You run the simulation. Keep continuity intact. "
                "Hold tone, realism, and emotion consistent. "
                "Do not summarize unseen events, do not repeat identical beats, and do not control the player. "
                "Wait for new input once the world has reacted."
            ),
        },
        "recentLog": recent,
        "relatedLog": related,
    }

# -------------------------------------------------------------------
# ROOT
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Life Simulation Backend v18.0 — Full-Continuity Engine Online."}
