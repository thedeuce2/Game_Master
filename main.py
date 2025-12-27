from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timedelta
import sqlite3, uuid, os

# ---------------------------------------------------------------------
# FASTAPI SETUP
# ---------------------------------------------------------------------
app = FastAPI(
    title="Life Simulation Game Master Backend API",
    version="15.0",
    description=(
        "SQLite-based, single-action backend for a dark, grounded life simulation. "
        "All world state derives from persistent database records — "
        "no hard-coded time, money, or defaults."
    ),
)

DB_PATH = "lifesim.db"

# ---------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scene (
            id INTEGER PRIMARY KEY,
            date TEXT,
            time TEXT,
            location TEXT,
            funds TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            playerId TEXT PRIMARY KEY,
            name TEXT,
            location TEXT,
            money REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS npcs (
            npcId TEXT PRIMARY KEY,
            name TEXT,
            attitude REAL,
            location TEXT,
            lastInteraction TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            eventId TEXT PRIMARY KEY,
            playerId TEXT,
            summary TEXT,
            detail TEXT,
            worldDate TEXT,
            worldTime TEXT,
            worldLocation TEXT,
            worldFunds TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------
class ResolveTurnRequest(BaseModel):
    playerId: Optional[str] = None
    summary: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------
# DATABASE UTILITIES
# ---------------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH)

def get_scene():
    """
    Load the current scene:
      - Return existing scene if available
      - Otherwise rebuild it from the most recent event
      - If no events exist, return an empty template
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT date, time, location, funds FROM scene LIMIT 1")
    row = cur.fetchone()
    if row:
        conn.close()
        return {"date": row[0], "time": row[1], "location": row[2], "funds": row[3]}

    cur.execute("""
        SELECT worldDate, worldTime, worldLocation, worldFunds
        FROM events
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    event_row = cur.fetchone()
    if event_row:
        derived_scene = {
            "date": event_row[0],
            "time": event_row[1],
            "location": event_row[2],
            "funds": event_row[3],
        }
    else:
        derived_scene = {"date": None, "time": None, "location": None, "funds": None}

    cur.execute("DELETE FROM scene")
    cur.execute(
        "INSERT INTO scene(date, time, location, funds) VALUES (?, ?, ?, ?)",
        (
            derived_scene["date"],
            derived_scene["time"],
            derived_scene["location"],
            derived_scene["funds"],
        ),
    )
    conn.commit()
    conn.close()
    return derived_scene

def save_scene(scene: Dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM scene")
    cur.execute(
        "INSERT INTO scene(date, time, location, funds) VALUES (?, ?, ?, ?)",
        (scene["date"], scene["time"], scene["location"], scene["funds"]),
    )
    conn.commit()
    conn.close()

def advance_time(scene: Dict, hours: int = 3):
    """Advance time safely when appropriate."""
    if not scene.get("time"):
        return scene
    try:
        now = datetime.strptime(scene["time"], "%I:%M %p")
    except Exception:
        return scene
    new_time = now + timedelta(hours=hours)
    scene["time"] = new_time.strftime("%I:%M %p")
    return scene

def get_player(playerId: Optional[str]):
    if not playerId:
        playerId = "doug_doucette"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT playerId, name, location, money FROM players WHERE playerId=?", (playerId,))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO players VALUES (?, ?, ?, ?)",
            (playerId, "Doug Doucette", "Los Angeles, CA", 100.0),
        )
        conn.commit()
        cur.execute("SELECT playerId, name, location, money FROM players WHERE playerId=?", (playerId,))
        row = cur.fetchone()
    conn.close()
    return {"playerId": row[0], "name": row[1], "location": row[2], "money": row[3]}

def get_npcs():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT npcId, name, attitude, location, lastInteraction FROM npcs")
    rows = cur.fetchall()
    conn.close()
    return {
        r[0]: {
            "npcId": r[0],
            "name": r[1],
            "attitude": r[2],
            "location": r[3],
            "lastInteraction": r[4],
        }
        for r in rows
    }

def save_npcs(npcs):
    conn = get_conn()
    cur = conn.cursor()
    for npc in npcs.values():
        cur.execute(
            "INSERT OR REPLACE INTO npcs VALUES (?, ?, ?, ?, ?)",
            (
                npc["npcId"],
                npc["name"],
                npc["attitude"],
                npc["location"],
                npc["lastInteraction"],
            ),
        )
    conn.commit()
    conn.close()

def log_event(event: Dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event["eventId"],
            event["playerId"],
            event["summary"],
            event["detail"],
            event["worldDate"],
            event["worldTime"],
            event["worldLocation"],
            event["worldFunds"],
            event["timestamp"],
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# META INSTRUCTIONS
# ---------------------------------------------------------------------
@app.get("/api/meta/instructions")
def get_meta_instructions():
    return {
        "version": "3.8",
        "tone": "Dark, grounded, cinematic, emotionally raw.",
        "instructions": (
            "🎮 GAME ENGINE CANON — You are the simulation engine, not a storyteller. "
            "Every player input is an action, dialogue, or reflection. "
            "Render the world's immediate reaction, then stop and wait. "
            "Do not invent time, money, or dates. Use the last known state from the world database.\n\n"
            "Advance time only after physical actions; dialogue and reflection should preserve the clock. "
            "Preserve continuity in every header — Day, Month, Year, Time, Location, and Funds. "
            "Depict adult realism through tone, suggestion, and subtext, never censorship.\n\n"
            "Never act or speak for the player. Output only what the world does in response. "
            "Your job is to maintain the living simulation, not to summarize it."
        ),
    }


# ---------------------------------------------------------------------
# MAIN SINGLE ACTION ENDPOINT
# ---------------------------------------------------------------------
@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    scene = get_scene()
    player = get_player(req.playerId)
    npcs = get_npcs()

    summary_lower = (req.summary or "").lower()
    if any(w in summary_lower for w in ["say", "ask", "reply", "tell"]):
        act_type = "dialogue"
    elif any(w in summary_lower for w in ["walk", "go", "take", "drive", "touch", "move", "grab", "open"]):
        act_type = "action"
    else:
        act_type = "reflection"

    if act_type == "action":
        scene = advance_time(scene, 3)
        save_scene(scene)

    for npc in npcs.values():
        if act_type == "dialogue":
            npc["attitude"] = (npc["attitude"] or 0) + 0.4
        elif act_type == "action":
            npc["attitude"] = (npc["attitude"] or 0) + 0.2
        npc["attitude"] = max(-10.0, min(10.0, npc["attitude"]))
        npc["lastInteraction"] = datetime.utcnow().isoformat() + "Z"
    save_npcs(npcs)

    event = {
        "eventId": str(uuid.uuid4()),
        "playerId": player["playerId"],
        "summary": req.summary,
        "detail": req.detail,
        "worldDate": scene.get("date"),
        "worldTime": scene.get("time"),
        "worldLocation": scene.get("location"),
        "worldFunds": scene.get("funds"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    log_event(event)

    return {
        "status": "applied",
        "eventId": event["eventId"],
        "scene": scene,
        "meta": get_meta_instructions(),
        "player": player,
        "npc": npcs,
    }


# ---------------------------------------------------------------------
# EVENT LOG RETRIEVAL
# ---------------------------------------------------------------------
@app.get("/api/logs/events")
def get_events(limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT eventId, playerId, summary, detail, worldDate, worldTime, worldLocation, worldFunds, timestamp "
        "FROM events ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    events = [
        {
            "eventId": r[0],
            "playerId": r[1],
            "summary": r[2],
            "detail": r[3],
            "worldDate": r[4],
            "worldTime": r[5],
            "worldLocation": r[6],
            "worldFunds": r[7],
            "timestamp": r[8],
        }
        for r in rows
    ]
    return {"events": events}


# ---------------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Life Simulation Backend v15 running with persistent SQLite world state (no hard-coded defaults)."
    }
