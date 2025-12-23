from fastapi import FastAPI, Query, Body, Path, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os, json, uuid, random, re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI(
    title="Life Simulation Backend API",
    version="5.0",
    description="Dark, mature life-simulation backend with canonical continuity and storytelling enforcement.",
)

# -------------------------------------------------------------------
# File constants
# -------------------------------------------------------------------

GAME_STATE_FILE = "game_state.json"
EVENT_LOG_FILE = "event_log.jsonl"
INTENTS_FILE = "intents.jsonl"
PLAYERS_FILE = "players.json"
STATIC_DIR = "static"
PDF_DIR = os.path.join(STATIC_DIR, "logs")

os.makedirs(PDF_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -------------------------------------------------------------------
# Utility I/O
# -------------------------------------------------------------------

def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _append_jsonl(path: str, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# -------------------------------------------------------------------
# Core Models
# -------------------------------------------------------------------

class ActorRef(BaseModel):
    role: str
    playerId: Optional[str] = None
    npcId: Optional[str] = None

class Balance(BaseModel):
    currency: str
    amount: float

class MoneyDelta(BaseModel):
    ownerType: str
    ownerId: str
    currency: str
    amount: float
    reason: Optional[str] = None

class Item(BaseModel):
    name: str
    amount: float
    value: Optional[float] = None
    props: Optional[Dict[str, Any]] = None

class InventoryDelta(BaseModel):
    ownerType: str
    ownerId: str
    op: str
    item: Item
    reason: Optional[str] = None

class RelationshipDelta(BaseModel):
    sourceId: str
    targetId: str
    targetType: str
    attitudeChange: float
    publicShift: Optional[float] = None
    notes: Optional[str] = None

class KnowledgeScope(BaseModel):
    visibility: str
    observedByNpcIds: List[str] = Field(default_factory=list)
    observedByPlayer: bool = True
    hiddenFromNpcIds: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    notes: Optional[str] = None

class EventInput(BaseModel):
    actor: ActorRef
    type: str
    summary: str
    details: Optional[str] = None
    feeling: Optional[str] = None
    moneyDeltas: List[MoneyDelta] = Field(default_factory=list)
    inventoryDeltas: List[InventoryDelta] = Field(default_factory=list)
    relationshipDeltas: List[RelationshipDelta] = Field(default_factory=list)
    knowledgeScope: Optional[KnowledgeScope] = None

class LoggedEvent(BaseModel):
    eventId: Optional[str] = None
    timestamp: Optional[str] = None
    playerId: Optional[str] = None
    sceneId: Optional[str] = None
    summary: str
    detail: Optional[str] = None
    outcomes: List[EventInput] = Field(default_factory=list)
    notes: Optional[str] = None

    # Cinematic header info
    worldDate: Optional[str] = None
    worldTime: Optional[str] = None
    worldLocation: Optional[str] = None
    worldFunds: Optional[str] = None

class PlayerStats(BaseModel):
    money: float = 0.0

class Player(BaseModel):
    playerId: str
    name: Optional[str] = None
    location: Optional[str] = None
    stats: PlayerStats = Field(default_factory=PlayerStats)
    wallets: List[Balance] = Field(default_factory=list)

class HistoryQuery(BaseModel):
    playerId: Optional[str] = None
    sceneId: Optional[str] = None
    npcIds: List[str] = Field(default_factory=list)
    limit: int = 50
    sort: str = "desc"

class PrecheckLatestProposalData(BaseModel):
    characterIds: List[str] = Field(default_factory=list)
    involvedNpcIds: List[str] = Field(default_factory=list)
    moneyDeltas: List[MoneyDelta] = Field(default_factory=list)
    inventoryDeltas: List[InventoryDelta] = Field(default_factory=list)
    relationshipDeltas: List[RelationshipDelta] = Field(default_factory=list)

class PrecheckLatestProposal(BaseModel):
    summary: Optional[str] = None
    data: Optional[PrecheckLatestProposalData] = None

class PrecheckRequest(BaseModel):
    playerId: Optional[str] = None
    historyQuery: Optional[HistoryQuery] = None
    latestProposal: Optional[PrecheckLatestProposal] = None
    checks: List[str] = Field(default_factory=list)

class PrecheckResult(BaseModel):
    summary: str
    logicConsistent: bool
    knowledgeLeaksDetected: bool
    npcIndividualityMaintained: bool
    gmAuthorityRespected: bool
    storyAdvancing: bool
    errors: List[str] = Field(default_factory=list)

# -------------------------------------------------------------------
# Meta endpoints
# -------------------------------------------------------------------

@app.get("/api/meta/instructions")
def get_meta_instructions():
    return {
        "version": "2.0",
        "tone": "Dark, mature, character-driven. Influences: Stephen King, Palahniuk, Ellis.",
        "instructions": (
            "You are the Game Master of a dark, mature life simulation. "
            "Maintain player autonomy, individuality among NPCs, and escalating tension. "
            "Always perform gpt-precheck and respect canonical continuity."
        ),
    }

@app.get("/api/meta/directives")
def get_storytelling_directives():
    """
    Canonical storytelling and simulation rules for the GPT front-end.
    """
    return {
        "version": "3.0",
        "header_format": {
            "example": {
                "date": "📅 Day 14, March 1998",
                "time": "⏰ 11:47 PM",
                "location": "📍 The Drowned Motel, Room 12",
                "funds": "💰 $42.00"
            }
        },
        "directives": {
            "continuity": "Review prior events before every continuation. Maintain canonical consistency and time realism.",
            "autonomy": "Never speak, act, or think for the player.",
            "npc_realism": "NPCs know only what they’ve seen or been told.",
            "tone": "Dark, human, grounded. No censorship, but stay psychological.",
            "dialogue": "Never summarize pivotal scenes; let them play out.",
            "header": "Start each major scene with Day, Month, Year, Time, Location, and Funds.",
            "time": "Advance time logically between beats.",
            "rating": "18+ themes allowed; realism over propriety.",
            "persistence": "The world continues unseen; actions have lasting impact."
        }
    }

# -------------------------------------------------------------------
# GPT Precheck
# -------------------------------------------------------------------

@app.post("/api/gpt-precheck", response_model=PrecheckResult)
def gpt_precheck(payload: PrecheckRequest):
    summary = payload.latestProposal.summary if payload.latestProposal else ""
    errors = []

    # Canonical continuity
    logic_consistent = True
    if not payload.historyQuery or payload.historyQuery.limit < 1:
        logic_consistent = False
        errors.append("Missing history context for continuity check.")

    # NPC omniscience detection
    knowledge_leaks_detected = "knew something they couldn’t" in summary.lower()
    if knowledge_leaks_detected:
        errors.append("Possible NPC omniscience detected.")

    # NPC individuality
    individuality_ok = True
    if payload.latestProposal and payload.latestProposal.data:
        ids = payload.latestProposal.data.involvedNpcIds
        if len(ids) != len(set(ids)):
            individuality_ok = False
            errors.append("NPC duplication detected.")

    # Player autonomy
    autonomy_ok = True
    if any(phrase in summary.lower() for phrase in ["you say", "you think", "you feel"]):
        autonomy_ok = False
        errors.append("Player autonomy violation: GPT spoke for the user.")

    # Story advancing?
    story_advancing = len(summary.strip()) > 20 and not knowledge_leaks_detected

    return PrecheckResult(
        summary=summary or "No summary provided",
        logicConsistent=logic_consistent,
        knowledgeLeaksDetected=knowledge_leaks_detected,
        npcIndividualityMaintained=individuality_ok,
        gmAuthorityRespected=autonomy_ok,
        storyAdvancing=story_advancing,
        errors=errors,
    )

# -------------------------------------------------------------------
# Player Handling
# -------------------------------------------------------------------

def _load_players():
    return _read_json(PLAYERS_FILE, {})

def _save_players(players):
    _write_json(PLAYERS_FILE, players)

@app.get("/api/player/{playerId}", response_model=Player)
def get_player(playerId: str):
    players = _load_players()
    if playerId not in players:
        player = Player(playerId=playerId)
        players[playerId] = player.model_dump()
        _save_players(players)
        return player
    return Player(**players[playerId])

@app.patch("/api/player/{playerId}", response_model=Player)
def update_player(playerId: str, payload: Dict[str, Any]):
    players = _load_players()
    existing = players.get(playerId, Player(playerId=playerId).model_dump())
    player = Player(**existing)

    if payload.get("name"): player.name = payload["name"]
    if payload.get("location"): player.location = payload["location"]
    if payload.get("stats"): player.stats = PlayerStats(**payload["stats"])
    if payload.get("wallets"): player.wallets = [Balance(**b) for b in payload["wallets"]]

    players[playerId] = player.model_dump()
    _save_players(players)
    return player

# -------------------------------------------------------------------
# Turns & Event Logging
# -------------------------------------------------------------------

@app.post("/api/turns/resolve")
def resolve_turn(req: Dict[str, Any]):
    playerId = req.get("playerId")
    sceneId = req.get("sceneId")
    outcomes = req.get("outcomes", [])
    meta = req.get("review", {}).get("metadata", {}) if req.get("review") else {}

    count = 0
    for o in outcomes:
        e = LoggedEvent(
            eventId=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            playerId=playerId,
            sceneId=sceneId,
            summary=o.get("summary", ""),
            detail=o.get("details", ""),
            outcomes=[],
            worldDate=meta.get("worldDate"),
            worldTime=meta.get("worldTime"),
            worldLocation=meta.get("worldLocation"),
            worldFunds=meta.get("worldFunds"),
        )
        _append_jsonl(EVENT_LOG_FILE, e.model_dump())
        count += 1

    return {"status": "applied", "numEvents": count}

# -------------------------------------------------------------------
# Scene State Snapshot
# -------------------------------------------------------------------

@app.get("/api/state/scene")
def get_scene_state(playerId: Optional[str] = Query(None)):
    latest_event = None
    if os.path.exists(EVENT_LOG_FILE):
        with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                try:
                    e = json.loads(line)
                    if playerId and e.get("playerId") != playerId:
                        continue
                    latest_event = e
                    break
                except json.JSONDecodeError:
                    continue

    if not latest_event:
        return {
            "date": "Day 1, January 1998",
            "time": "7:00 AM",
            "location": "Unknown",
            "funds": "$0.00"
        }

    return {
        "date": latest_event.get("worldDate", "Unknown"),
        "time": latest_event.get("worldTime", "Unknown"),
        "location": latest_event.get("worldLocation", "Unknown"),
        "funds": latest_event.get("worldFunds", "Unknown"),
    }

# -------------------------------------------------------------------
# PDF Generation
# -------------------------------------------------------------------

def generate_pdf_from_log(playerId: Optional[str] = None) -> Optional[str]:
    if not os.path.exists(EVENT_LOG_FILE):
        return None
    events = []
    with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                if playerId and e.get("playerId") != playerId:
                    continue
                events.append(e)
            except json.JSONDecodeError:
                continue
    events = sorted(events, key=lambda e: e.get("timestamp", ""))
    filename = f"log_{playerId or 'all'}.pdf"
    pdf_path = os.path.join(PDF_DIR, filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    w, h = letter
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Life Simulation Log ({playerId or 'All Players'})")
    y -= 24
    c.setFont("Helvetica", 9)
    for e in events:
        line = f"[{e.get('timestamp')}] {e.get('summary')}"
        for chunk in [line[i:i+100] for i in range(0, len(line), 100)]:
            if y <= 60:
                c.showPage(); y = h - 50; c.setFont("Helvetica", 9)
            c.drawString(50, y, chunk); y -= 12
        y -= 4
    c.save()
    return pdf_path

@app.get("/api/logs/pdf")
def get_pdf_log(request: Request, playerId: Optional[str] = Query(None)):
    path = generate_pdf_from_log(playerId)
    if not path:
        return {"pdfUrl": None, "generatedAt": None}
    base = str(request.base_url).rstrip("/")
    rel = os.path.relpath(path, STATIC_DIR).replace("\\", "/")
    return {
        "pdfUrl": f"{base}/static/{rel}",
        "generatedAt": datetime.utcnow().isoformat() + "Z"
    }

# -------------------------------------------------------------------
# Run message
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "Life Simulation Backend v5 active."}
