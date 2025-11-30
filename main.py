from fastapi import FastAPI, Query, Body, Path, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import random
import re
import os
import json
from datetime import datetime
import uuid

# PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI(
    title="Life Simulation Backend API",
    version="4.0",
    description=(
        "Event-first backend for a dark, mature life-simulation game. "
        "Provides logging, players, wallets, inventory, and meta endpoints "
        "for a narrative-heavy Game Master."
    ),
)

# -------------------------------------------------------------------
# Files & constants
# -------------------------------------------------------------------

GAME_STATE_FILE = "game_state.json"
EVENT_LOG_FILE = "event_log.jsonl"
INTENTS_FILE = "intents.jsonl"
PLAYERS_FILE = "players.json"

# PDF logs live under /static/logs so they can be served as files
STATIC_DIR = "static"
PDF_DIR = os.path.join(STATIC_DIR, "logs")

# Ensure directories exist at startup
os.makedirs(PDF_DIR, exist_ok=True)

# Mount /static so PDFs are accessible at /static/...
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -------------------------------------------------------------------
# Utility functions for simple storage
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
# Core schema models (matching your OpenAPI)
# -------------------------------------------------------------------


class ActorRef(BaseModel):
    role: str  # "player", "npc", "system", "gm"
    playerId: Optional[str] = None
    npcId: Optional[str] = None


class Balance(BaseModel):
    currency: str
    amount: float


class MoneyDelta(BaseModel):
    ownerType: str  # "player" | "npc"
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
    ownerType: str  # "player" | "npc"
    ownerId: str
    op: str         # "add" | "remove" | "set"
    item: Item
    reason: Optional[str] = None


class RelationshipDelta(BaseModel):
    sourceId: str
    targetId: str
    targetType: str  # "npc" | "player"
    attitudeChange: float
    publicShift: Optional[float] = None
    notes: Optional[str] = None


class KnowledgeScope(BaseModel):
    visibility: str  # "public" | "private" | "secret"
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


class HistoryQuery(BaseModel):
    playerId: Optional[str] = None
    sceneId: Optional[str] = None
    npcIds: List[str] = Field(default_factory=list)
    limit: int = 50
    sort: str = "desc"  # "asc" | "desc"


class PrecheckResult(BaseModel):
    summary: str
    logicConsistent: bool
    knowledgeLeaksDetected: bool
    npcIndividualityMaintained: bool
    gmAuthorityRespected: bool
    storyAdvancing: bool
    errors: List[str] = Field(default_factory=list)


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


class PlayerStats(BaseModel):
    money: float = 0.0


class Player(BaseModel):
    playerId: str
    name: Optional[str] = None
    location: Optional[str] = None
    stats: PlayerStats = Field(default_factory=PlayerStats)
    wallets: List[Balance] = Field(default_factory=list)


class Inventory(BaseModel):
    ownerType: str  # "player" | "npc"
    ownerId: str
    items: List[Item] = Field(default_factory=list)


class LoggedEvent(BaseModel):
    eventId: Optional[str] = None
    timestamp: Optional[str] = None
    playerId: Optional[str] = None
    sceneId: Optional[str] = None
    summary: str
    detail: Optional[str] = None
    outcomes: List[EventInput] = Field(default_factory=list)
    notes: Optional[str] = None


class IntentData(BaseModel):
    summary: str
    data: Optional[Dict[str, Any]] = None


class SubmitIntentRequest(BaseModel):
    playerId: str
    intent: IntentData
    sceneId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ResolveReviewConfig(BaseModel):
    include: bool = True
    historyQuery: Optional[HistoryQuery] = None
    checks: List[str] = Field(default_factory=list)


class ResolveTurnRequest(BaseModel):
    playerId: str
    sceneId: Optional[str] = None
    basedOnEventIds: List[str] = Field(default_factory=list)
    outcomes: List[EventInput] = Field(default_factory=list)
    review: Optional[ResolveReviewConfig] = None


# Story references models

class StoryReferencesRequest(BaseModel):
    description: str
    tags: Optional[List[str]] = None


class StoryReferenceItem(BaseModel):
    theme: str
    works: List[str]


class StoryReferencesResponse(BaseModel):
    references: List[StoryReferenceItem]


# Character generator models (still used internally if you want)

class CharacterRequest(BaseModel):
    name: str
    background: Optional[str] = None
    race: Optional[str] = None


class CharacterResponse(BaseModel):
    name: str
    background: Optional[str] = None
    race: Optional[str] = None
    stats: Dict[str, int]
    hp: int
    buffs: List[str] = Field(default_factory=list)


class UpdatePlayerRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    stats: Optional[PlayerStats] = None
    wallets: Optional[List[Balance]] = None


# -------------------------------------------------------------------
# State save/load (kept for completeness; not in schema)
# -------------------------------------------------------------------


@app.post("/save_state")
def save_state(state: dict = Body(...)):
    """
    Save an arbitrary game state blob. Useful as an emergency snapshot.
    """
    _write_json(GAME_STATE_FILE, state)
    return {"status": "saved"}


@app.get("/load_state")
def load_state():
    if not os.path.exists(GAME_STATE_FILE):
        return {"error": "No saved state found"}
    state = _read_json(GAME_STATE_FILE, {})
    return {"state": state}


# -------------------------------------------------------------------
# Dice + character generator (not exposed in trimmed schema, but available)
# -------------------------------------------------------------------


def parse_dice(dice_expr: str):
    pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, dice_expr.replace(" ", ""))
    if not match:
        return None
    num = int(match.group(1)) if match.group(1) else 1
    die = int(match.group(2))
    mod = int(match.group(3)) if match.group(3) else 0
    return num, die, mod


@app.get("/roll_dice")
def roll_dice(
    dice: str = Query(
        "1d20",
        description="Dice expression, e.g., '2d6+1', '1d20', '3d8-2'",
    ),
    label: Optional[str] = Query(
        None, description="Optional description of the roll"
    ),
) -> Dict[str, Any]:
    parsed = parse_dice(dice)
    if not parsed:
        return {
            "error": "Invalid dice format. Use NdM+X, e.g., 2d6+1, 1d20, 4d8-2."
        }
    num, die, mod = parsed
    rolls = [random.randint(1, die) for _ in range(num)]
    total = sum(rolls) + mod
    result = {
        "dice": dice,
        "label": label,
        "rolls": rolls,
        "modifier": mod,
        "total": total,
    }
    if label:
        result["label"] = label
    return result


def roll_stat():
    dice = [random.randint(1, 6) for _ in range(4)]
    dice.remove(min(dice))
    return sum(dice)


def generate_stats():
    return {
        "strength": roll_stat(),
        "dexterity": roll_stat(),
        "constitution": roll_stat(),
        "intelligence": roll_stat(),
        "wisdom": roll_stat(),
        "charisma": roll_stat(),
    }


@app.post("/create_character", response_model=CharacterResponse)
def create_character(request: CharacterRequest):
    stats = generate_stats()
    buffs: List[str] = []
    if request.race:
        race_lower = request.race.lower()
        if "orc" in race_lower:
            stats["strength"] += 2
            buffs.append("Orc: +2 Strength")
        elif "elf" in race_lower:
            stats["dexterity"] += 2
            buffs.append("Elf: +2 Dexterity")
        elif "dwarf" in race_lower:
            stats["constitution"] += 2
            buffs.append("Dwarf: +2 Constitution")
        elif "human" in race_lower:
            for k in stats:
                stats[k] += 1
            buffs.append("Human: +1 to all stats")
    hp = 8 + ((stats["constitution"] - 10) // 2)
    return {
        "name": request.name,
        "background": request.background,
        "race": request.race,
        "stats": stats,
        "hp": hp,
        "buffs": buffs,
    }


@app.get("/remind_rules")
def remind_rules():
    return {
        "reminder": (
            "Reminder: All gameplay must follow the core rules. "
            "No skipping dice rolls, no fudging results. "
            "All mechanical actions use the API. "
            "Storytelling, roleplay, and description are freeform, "
            "but outcomes are based on rolls and stats."
        )
    }


@app.post("/advance_relationship")
def advance_relationship(
    character_name: str = Body(...),
    target_name: str = Body(...),
    stat: str = Body(..., description="Stat to use (e.g., 'charisma')"),
    difficulty: int = Body(12, description="Difficulty class (DC)"),
    bonus: int = Body(0, description="Additional bonus to apply"),
):
    # Demo-only stand-in for real character sheets.
    fake_characters = {
        "Alice": {"charisma": 14, "wisdom": 10},
        "Bob": {"charisma": 10, "wisdom": 12},
    }
    char_stats = fake_characters.get(
        character_name, {"charisma": 10, "wisdom": 10}
    )
    stat_score = char_stats.get(stat.lower(), 10)
    stat_mod = (stat_score - 10) // 2  # D&D-style modifier

    roll = random.randint(1, 20)
    total = roll + stat_mod + bonus
    success = total >= difficulty

    return {
        "character": character_name,
        "target": target_name,
        "stat": stat,
        "stat_score": stat_score,
        "stat_mod": stat_mod,
        "roll": roll,
        "bonus": bonus,
        "difficulty": difficulty,
        "total": total,
        "success": success,
        "result": "Relationship improved!"
        if success
        else "No improvement this time.",
    }


# -------------------------------------------------------------------
# /api/meta/instructions – canonical GM meta-instructions
# -------------------------------------------------------------------


@app.get("/api/meta/instructions")
def get_meta_instructions():
    """
    Returns meta-instructions for the Game Master.
    The GPT should use these if it wants a backend copy of its role & tone.
    """
    return {
        "version": "1.0.0",
        "tone": (
            "Dark, mature, character-driven. Influences: Stephen King, "
            "Chuck Palahniuk, Caroline Kepnes, Bret Easton Ellis."
        ),
        "instructions": (
            "You are the Game Master of a dark, mature life simulation. "
            "Maintain player autonomy, individual NPCs, and escalating drama. "
            'Always call precheck and log tools before responding. '
            "Never break character; only step out of the game when the user "
            "speaks in parentheses."
        ),
    }


# -------------------------------------------------------------------
# /api/gpt-precheck – required precheck before every narrative response
# -------------------------------------------------------------------


@app.post("/api/gpt-precheck", response_model=PrecheckResult)
def gpt_precheck(payload: PrecheckRequest):
    """
    Lightweight implementation: always marks story as advancing and logic as consistent.
    The GPT should still treat this as a mandatory precheck before it responds.
    """
    summary = payload.latestProposal.summary if payload.latestProposal else ""
    return PrecheckResult(
        summary=summary or "No summary provided",
        logicConsistent=True,
        knowledgeLeaksDetected=False,
        npcIndividualityMaintained=True,
        gmAuthorityRespected=True,
        storyAdvancing=True,
        errors=[],
    )


# -------------------------------------------------------------------
# /api/story/references – literary echoes for scene description
# -------------------------------------------------------------------


@app.post("/api/story/references", response_model=StoryReferencesResponse)
def get_story_references(req: StoryReferencesRequest):
    desc_lower = req.description.lower()
    refs: List[StoryReferenceItem] = []

    if any(t in desc_lower for t in ["small town", "rural", "isolated", "fog"]):
        refs.append(
            StoryReferenceItem(
                theme="Isolated community horror",
                works=[
                    "Stephen King – 'Salem's Lot",
                    "Thomas Tryon – 'Harvest Home'",
                ],
            )
        )

    if any(t in desc_lower for t in ["obsession", "stalker", "parasocial"]):
        refs.append(
            StoryReferenceItem(
                theme="Obsessive, stalkerish POV",
                works=[
                    "Caroline Kepnes – 'You'",
                    "Bret Easton Ellis – 'American Psycho'",
                ],
            )
        )

    if any(t in desc_lower for t in ["body", "violence", "brutal"]):
        refs.append(
            StoryReferenceItem(
                theme="Visceral, bodily horror",
                works=[
                    "Chuck Palahniuk – 'Haunted'",
                    "Clive Barker – 'Books of Blood'",
                ],
            )
        )

    if not refs:
        refs.append(
            StoryReferenceItem(
                theme="Dark, internalized psychological tension",
                works=[
                    "Stephen King – 'Misery'",
                    "Bret Easton Ellis – 'Less Than Zero'",
                ],
            )
        )

    return StoryReferencesResponse(references=refs)


# -------------------------------------------------------------------
# Players: /api/player/{playerId}
# -------------------------------------------------------------------


def _load_players() -> Dict[str, dict]:
    return _read_json(PLAYERS_FILE, {})


def _save_players(players: Dict[str, dict]):
    _write_json(PLAYERS_FILE, players)


@app.get("/api/player/{playerId}", response_model=Player)
def get_player(
    playerId: str = Path(..., description="Unique player ID"),
):
    players = _load_players()
    data = players.get(playerId)
    if not data:
        # create a minimal default on-the-fly
        player = Player(playerId=playerId)
        players[playerId] = player.model_dump()
        _save_players(players)
        return player
    return Player(**data)


@app.patch("/api/player/{playerId}", response_model=Player)
def update_player(
    playerId: str,
    payload: UpdatePlayerRequest,
):
    players = _load_players()
    existing = players.get(playerId)

    if existing:
        player = Player(**existing)
    else:
        player = Player(playerId=playerId)

    if payload.name is not None:
        player.name = payload.name
    if payload.location is not None:
        player.location = payload.location
    if payload.stats is not None:
        player.stats = payload.stats
    if payload.wallets is not None:
        player.wallets = payload.wallets

    players[playerId] = player.model_dump()
    _save_players(players)
    return player


# -------------------------------------------------------------------
# Turns: submit intent & resolve
# -------------------------------------------------------------------


@app.post("/api/turns/submit-intent")
def submit_intent(req: SubmitIntentRequest):
    """
    Store the player's declared intent for auditing or offline analysis.
    """
    record = req.model_dump()
    record["timestamp"] = datetime.utcnow().isoformat() + "Z"
    _append_jsonl(INTENTS_FILE, record)
    return {"status": "accepted"}


@app.post("/api/turns/resolve")
def resolve_turn(req: ResolveTurnRequest):
    """
    Apply outcomes as events. Real logic (wallet updates, NPC state, etc.)
    can be layered on later by replaying the log.
    """
    for outcome in req.outcomes:
        event = LoggedEvent(
            eventId=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            playerId=req.playerId,
            sceneId=req.sceneId,
            summary=outcome.summary,
            detail=outcome.details,
            outcomes=[outcome],
        )
        _append_jsonl(EVENT_LOG_FILE, event.model_dump())

    return {"status": "applied", "numEvents": len(req.outcomes)}


# -------------------------------------------------------------------
# PDF generation from log
# -------------------------------------------------------------------


def generate_pdf_from_log(playerId: Optional[str] = None) -> Optional[str]:
    """
    Read EVENT_LOG_FILE, filter by playerId if given, and generate a PDF
    summarizing all events. Returns the full path to the PDF.
    """
    events: List[dict] = []
    if not os.path.exists(EVENT_LOG_FILE):
        # No events yet; nothing to write
        return None

    with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if playerId and e.get("playerId") != playerId:
                continue
            events.append(e)

    # Sort by timestamp ascending
    events = sorted(events, key=lambda e: e.get("timestamp", ""))

    # Choose filename: per-player or global
    if playerId:
        safe_id = "".join(c for c in playerId if c.isalnum() or c in "-_")
        filename = f"log_{safe_id}.pdf"
    else:
        filename = "log_all.pdf"

    pdf_path = os.path.join(PDF_DIR, filename)

    # Build a simple text PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin

    title = f"Life Simulation Event Log ({playerId or 'all players'})"
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, title)
    y -= 24

    c.setFont("Helvetica", 10)
    for e in events:
        ts = e.get("timestamp", "")
        summary = e.get("summary", "")
        scene = e.get("sceneId", "")
        line = f"[{ts}] [scene: {scene}] {summary}"
        # crude wrapping
        max_chars = 110
        chunks = [line[i:i + max_chars] for i in range(0, len(line), max_chars)]
        for chunk in chunks:
            if y <= margin:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 10)
            c.drawString(margin, y, chunk)
            y -= 14
        # extra space between events
        y -= 6

    c.save()
    return pdf_path


# -------------------------------------------------------------------
# Logs & PDF endpoints
# -------------------------------------------------------------------


@app.post("/api/logs/events")
def append_event_log(event: LoggedEvent):
    if event.eventId is None:
        event.eventId = str(uuid.uuid4())
    if event.timestamp is None:
        event.timestamp = datetime.utcnow().isoformat() + "Z"

    _append_jsonl(EVENT_LOG_FILE, event.model_dump())
    return {"status": "ok", "eventId": event.eventId}


@app.get("/api/logs/events")
def get_event_log(
    playerId: Optional[str] = Query(None),
    sceneId: Optional[str] = Query(None),
    limit: int = Query(50),
):
    events: List[dict] = []
    if os.path.exists(EVENT_LOG_FILE):
        with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if playerId and e.get("playerId") != playerId:
                    continue
                if sceneId and e.get("sceneId") != sceneId:
                    continue
                events.append(e)

    events = sorted(
        events, key=lambda e: e.get("timestamp", ""), reverse=True
    )
    return {"events": events[:limit]}


@app.get("/api/logs/pdf")
def get_pdf_log(
    request: Request,
    playerId: Optional[str] = Query(
        None, description="Optional playerId to filter the log"
    ),
):
    """
    Generate (or refresh) a PDF log from the events and return a URL to download it.
    The GPT should call this after every turn and show pdfUrl to the player.
    """
    pdf_path = generate_pdf_from_log(playerId)
    if not pdf_path:
        return {"pdfUrl": None, "generatedAt": None}

    generatedAt = datetime.utcnow().isoformat() + "Z"

    # Build a URL like https://host/static/logs/filename.pdf
    base_url = str(request.base_url).rstrip("/")
    rel_path = os.path.relpath(pdf_path, STATIC_DIR).replace("\\", "/")
    pdf_url = f"{base_url}/static/{rel_path}"

    return {"pdfUrl": pdf_url, "generatedAt": generatedAt}


# -------------------------------------------------------------------
# Wallets & inventory: computed from event log
# -------------------------------------------------------------------


@app.get("/api/wallets/{ownerType}/{ownerId}/balances")
def get_balances(
    ownerType: str,
    ownerId: str,
    currency: Optional[str] = Query(
        None, description="Filter by specific currency"
    ),
):
    """
    Compute balances by replaying MoneyDeltas from the event log.
    """
    totals: Dict[str, float] = {}

    if os.path.exists(EVENT_LOG_FILE):
        with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for outcome in entry.get("outcomes", []):
                    for md in outcome.get("moneyDeltas", []):
                        if (
                            md.get("ownerType") == ownerType
                            and md.get("ownerId") == ownerId
                        ):
                            cur = md.get("currency")
                            amt = float(md.get("amount", 0))
                            totals[cur] = totals.get(cur, 0.0) + amt

    balances = [
        {"currency": cur, "amount": amt} for cur, amt in totals.items()
    ]
    if currency:
        balances = [b for b in balances if b["currency"] == currency]

    return {"balances": balances}


@app.get("/api/inventory/{ownerType}/{ownerId}/snapshot")
def get_inventory_snapshot(ownerType: str, ownerId: str):
    """
    Compute current inventory by replaying InventoryDeltas from the event log.
    """
    stock: Dict[str, Dict[str, Any]] = {}

    if os.path.exists(EVENT_LOG_FILE):
        with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for outcome in entry.get("outcomes", []):
                    for invd in outcome.get("inventoryDeltas", []):
                        if (
                            invd.get("ownerType") == ownerType
                            and invd.get("ownerId") == ownerId
                        ):
                            op = invd.get("op")
                            item_data = invd.get("item") or {}
                            name = item_data.get("name")
                            if not name:
                                continue

                            item = stock.get(name) or {
                                "name": name,
                                "amount": 0.0,
                                "value": item_data.get("value"),
                                "props": item_data.get("props"),
                            }

                            if op == "add":
                                item["amount"] = float(
                                    item.get("amount", 0)
                                ) + float(item_data.get("amount", 0))
                            elif op == "remove":
                                item["amount"] = float(
                                    item.get("amount", 0)
                                ) - float(item_data.get("amount", 0))
                            elif op == "set":
                                item["amount"] = float(
                                    item_data.get("amount", 0)
                                )

                            stock[name] = item

    items = [
        i for i in stock.values() if float(i.get("amount", 0)) != 0
    ]
    return {
        "ownerType": ownerType,
        "ownerId": ownerId,
        "items": items,
    }
