from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timedelta
import json
import os
import uuid

app = FastAPI(
    title="Life Simulation Game Master Backend API",
    version="13.0",
    description="Single-action simulation backend for a dark, grounded narrative life simulation."
)

# -------------------------------------------------------------------
# File paths and persistence setup
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
    detail: Optional[str] = None


class SceneState(BaseModel):
    date: str
    time: str
    location: str
    funds: str


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


class Player(BaseModel):
    playerId: str
    name: str = "Doug Doucette"
    location: str = "Los Angeles, CA"
    money: float = 100.0


class NPC(BaseModel):
    npcId: str
    name: str
    attitude: float = 0.0
    location: str = "Los Angeles, CA"
    lastInteraction: Optional[str] = None


# -------------------------------------------------------------------
# UTILITY FUNCTIONS
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
    if not os.path.exists(SCENE_FILE):
        scene = SceneState(
            date="Saturday, December 27, 2025",
            time="8:00 PM",
            location="Los Angeles, CA",
            funds="$100.00"
        )
        save_json(SCENE_FILE, scene.dict())
        return scene
    data = load_json(SCENE_FILE, {})
    return SceneState(**data)


def save_scene(scene: SceneState):
    save_json(SCENE_FILE, scene.dict())


def load_player(player_id: Optional[str]) -> Player:
    players = load_json(PLAYER_FILE, {})
    if not player_id:
        if "default" in players:
            player_data = players["default"]
        else:
            player = Player(playerId="doug_doucette")
            players["default"] = player.dict()
            save_json(PLAYER_FILE, players)
            return player
    else:
        if player_id in players:
            player_data = players[player_id]
        else:
            player = Player(playerId=player_id)
            players[player_id] = player.dict()
            save_json(PLAYER_FILE, players)
            return player
    return Player(**player_data)


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


def advance_time(scene: SceneState, hours: int = 3):
    try:
        now = datetime.strptime(scene.time, "%I:%M %p")
    except ValueError:
        now = datetime.strptime("8:00 PM", "%I:%M %p")
    new_time = now + timedelta(hours=hours)
    scene.time = new_time.strftime("%I:%M %p")
    return scene


# -------------------------------------------------------------------
# META INSTRUCTIONS – GOLDEN CANON
# -------------------------------------------------------------------
@app.get("/api/meta/instructions")
def get_meta_instructions():
    return {
        "version": "3.0",
        "tone": "Dark, mature, grounded, cinematic, and emotionally authentic.",
        "instructions": (
            "⚙️ GAME ENGINE DIRECTIVE (Golden Rule):\n\n"
            "You are not a storyteller — you are the simulation engine for a dark, mature life simulator. "
            "The player drives all dialogue, action, and reflection. "
            "You render the immediate world response and then STOP.\n\n"
            "Treat every player message as gameplay input — an action, dialogue, or reflection. "
            "Render consequences realistically and cinematically. "
            "Advance time only after meaningful action, not thoughts. "
            "Never skip ahead or summarize unseen events.\n\n"
            "The player’s autonomy is absolute. You never speak, think, or act for them. "
            "NPCs must remain unique, motivated, and emotionally human. "
            "They may swear, flirt, fight, fail, or fall in love — it’s your job to make them feel real.\n\n"
            "Romance, intimacy, and attraction are part of mature realism. "
            "Depict them through atmosphere, tone, and emotional weight — never clinical. "
            "Skirt the edge of policy by implication and subtext, not omission.\n\n"
            "Each scene begins with a cinematic header (Day, Month, Year, Time, Location, Funds). "
            "Carry forward continuity every turn, evolve relationships naturally, "
            "and advance the world logically with consequence and cause.\n\n"
            "When the player finishes a turn, wait. Do not continue. Await the next input. "
            "You are the world, not the protagonist."
        )
    }


# -------------------------------------------------------------------
# TURN RESOLUTION – ONE ACTION, COMPLETE LOOP
# -------------------------------------------------------------------
@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """The single unified simulation action."""
    scene = load_scene()
    player = load_player(req.playerId)
    npcs = load_npc_memory()

    # Infer action type (action/dialogue/reflection)
    action_type = "reflection"
    if any(x in req.summary.lower() for x in ["say", "ask", "tell", "reply", "respond", "shout"]):
        action_type = "dialogue"
    elif any(x in req.summary.lower() for x in ["walk", "go", "move", "take", "do", "grab", "drive", "touch", "kiss", "leave"]):
        action_type = "action"

    # Advance time only for physical actions
    if action_type == "action":
        scene = advance_time(scene, 3)
        save_scene(scene)

    # Basic NPC relationship update for realism
    if npcs:
        for npc in npcs.values():
            change = 0.0
            if action_type == "dialogue":
                change = 0.5
            elif action_type == "reflection":
                change = 0.0
            elif action_type == "action":
                change = 0.3
            npc.attitude = max(-10.0, min(10.0, npc.attitude + change))
            npc.lastInteraction = datetime.utcnow().isoformat() + "Z"
        save_npc_memory(npcs)

    # Log event
    event = Event(
        eventId=str(uuid.uuid4()),
        playerId=player.playerId,
        summary=req.summary,
        detail=req.detail,
        worldDate=scene.date,
        worldTime=scene.time,
        worldLocation=scene.location,
        worldFunds=scene.funds,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
    append_event(event)

    # Return unified response
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
# ROOT ENDPOINT
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Life Simulation Game Master Backend v13 running — single-action simulation engine online."
    }
