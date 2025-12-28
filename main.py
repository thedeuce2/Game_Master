from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import json
import os
import uuid

app = FastAPI(
    title="Life Simulation Game Master Backend API",
    version="FINAL-WORLD-AGNOSTIC",
    description=(
        "Authoritative backend for narrative simulations. "
        "No defaults, no safety fallbacks, no story assumptions — "
        "it only records and returns exactly what the AI sends."
    ),
)

# -------------------------------------------------------------------
# File paths
# -------------------------------------------------------------------
DATA_DIR = "static"
LOG_FILE = os.path.join(DATA_DIR, "events.jsonl")
SCENE_FILE = os.path.join(DATA_DIR, "scene_state.json")
PLAYER_FILE = os.path.join(DATA_DIR, "player_registry.json")
NPC_FILE = os.path.join(DATA_DIR, "npc_memory.json")
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------------------------------------------
# MODELS
# -------------------------------------------------------------------
class ResolveTurnRequest(BaseModel):
    playerId: Optional[str] = None
    summary: str
    detail: Optional[Any] = None


class SceneState(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    funds: Optional[str] = None


class Event(BaseModel):
    eventId: str
    playerId: str
    summary: str
    detail: Optional[str]
    worldDate: Optional[str]
    worldTime: Optional[str]
    worldLocation: Optional[str]
    worldFunds: Optional[str]
    timestamp: str


class Player(BaseModel):
    playerId: str
    name: Optional[str] = None
    location: Optional[str] = None
    money: Optional[float] = None


class NPC(BaseModel):
    npcId: str
    name: str
    attitude: float = 0.0
    location: Optional[str] = None
    lastInteraction: Optional[str] = None


# -------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_event(event: Event):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.dict(), ensure_ascii=False) + "\n")


def load_scene() -> SceneState:
    data = load_json(SCENE_FILE, {})
    return SceneState(**data)


def save_scene(scene: SceneState):
    save_json(SCENE_FILE, scene.dict())


def load_player(player_id: Optional[str]) -> Player:
    players = load_json(PLAYER_FILE, {})
    if not player_id:
        player_id = "default_player"
    if player_id in players:
        return Player(**players[player_id])
    player = Player(playerId=player_id)
    players[player_id] = player.dict()
    save_json(PLAYER_FILE, players)
    return player


def save_player(player: Player):
    players = load_json(PLAYER_FILE, {})
    players[player.playerId] = player.dict()
    save_json(PLAYER_FILE, players)


def load_npc_memory() -> Dict[str, NPC]:
    data = load_json(NPC_FILE, {})
    return {k: NPC(**v) for k, v in data.items()}


def save_npc_memory(npcs: Dict[str, NPC]):
    data = {k: v.dict() for k, v in npcs.items()}
    save_json(NPC_FILE, data)


# -------------------------------------------------------------------
# META INSTRUCTIONS — UNEDITED
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
            "Time progression is organic: estimate it logically based on the flow of events. "
            "Do not rely on backend defaults; read your last header for continuity.\n\n"
            "Preserve canonical consistency across every scene. "
            "Carry forward the latest header (Day, Month, Year, Time, Location, Funds). "
            "Adjust values only when events justify change — purchases, travel, waiting, sleep, etc. "
            "You are responsible for realism, not the backend.\n\n"
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
# TURN RESOLUTION — PURE AUTHORITATIVE MODE
# -------------------------------------------------------------------
@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """Record exactly what the AI sends. No defaults, no interference."""
    player = load_player(req.playerId)
    npcs = load_npc_memory()
    last_scene = load_scene()

    scene_data = {}
    if isinstance(req.detail, dict):
        scene_data = req.detail
    else:
        try:
            scene_data = json.loads(req.detail or "{}")
        except Exception:
            scene_data = {}

    # Only update keys that exist and have non-null values
    updated_scene = last_scene.dict()
    for key in ["date", "time", "location", "funds"]:
        api_key = f"world{key.capitalize()}"
        if api_key in scene_data and scene_data[api_key] not in [None, ""]:
            updated_scene[key] = scene_data[api_key]

    scene = SceneState(**updated_scene)
    save_scene(scene)

    # Update NPC timestamps only
    for npc in npcs.values():
        npc.lastInteraction = datetime.utcnow().isoformat() + "Z"
    save_npc_memory(npcs)

    # Log exactly what was received
    event = Event(
        eventId=str(uuid.uuid4()),
        playerId=player.playerId,
        summary=req.summary,
        detail=json.dumps(req.detail, ensure_ascii=False) if req.detail else None,
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
        "scene": scene.dict(),
        "meta": get_meta_instructions(),
        "player": player.dict(),
        "npc": {k: v.dict() for k, v in npcs.items()},
    }


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
    return {"message": "Life Simulation Backend — Pure Authoritative, World-Agnostic Mode Online."}
