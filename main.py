from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import random
import re
import os
import json

app = FastAPI()

GAME_STATE_FILE = "game_state.json"

@app.post("/save_state")
def save_state(state: dict = Body(...)):
    # Save the state to a local JSON file
    with open(GAME_STATE_FILE, "w") as f:
        json.dump(state, f)
    return {"status": "saved"}

@app.get("/load_state")
def load_state():
    if not os.path.exists(GAME_STATE_FILE):
        return {"error": "No saved state found"}
    with open(GAME_STATE_FILE, "r") as f:
        state = json.load(f)
    return {"state": state}

# --- DICE ROLLER ---
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
    dice: str = Query("1d20", description="Dice expression, e.g., '2d6+1', '1d20', '3d8-2'"),
    label: Optional[str] = Query(None, description="Optional description of the roll")
) -> Dict[str, Any]:
    parsed = parse_dice(dice)
    if not parsed:
        return {"error": "Invalid dice format. Use NdM+X, e.g., 2d6+1, 1d20, 4d8-2."}
    num, die, mod = parsed
    rolls = [random.randint(1, die) for _ in range(num)]
    total = sum(rolls) + mod
    result = {
        "dice": dice,
        "label": label,
        "rolls": rolls,
        "modifier": mod,
        "total": total
    }
    if label:
        result["label"] = label
    return result

# --- CHARACTER GENERATOR ---
def roll_stat():
    dice = [random.randint(1,6) for _ in range(4)]
    dice.remove(min(dice))
    return sum(dice)

def generate_stats():
    return {
        "strength": roll_stat(),
        "dexterity": roll_stat(),
        "constitution": roll_stat(),
        "intelligence": roll_stat(),
        "wisdom": roll_stat(),
        "charisma": roll_stat()
    }

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
    buffs: Optional[List[str]] = []

@app.post("/create_character", response_model=CharacterResponse)
def create_character(request: CharacterRequest):
    stats = generate_stats()
    buffs = []
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
        "buffs": buffs
    }
    
@app.get("/remind_rules")
def remind_rules():
    return {
        "reminder": (
            "Reminder: All gameplay must follow the core rules. "
            "No skipping dice rolls, no fudging results. "
            "All mechanical actions use the API. "
            "Storytelling, roleplay, and description are freeform, but outcomes are based on rolls and stats."
        )
    }

from fastapi import Body

@app.post("/advance_relationship")
def advance_relationship(
    character_name: str = Body(...),
    target_name: str = Body(...),
    stat: str = Body(..., description="Stat to use (e.g., 'charisma')"),
    difficulty: int = Body(12, description="Difficulty class (DC) for relationship improvement"),
    bonus: int = Body(0, description="Additional bonus to apply to the roll")
):
    # For demo, fake a character sheet; in a real system, fetch from saved state.
    fake_characters = {
        "Alice": {"charisma": 14, "wisdom": 10},
        "Bob": {"charisma": 10, "wisdom": 12}
    }
    char_stats = fake_characters.get(character_name, {"charisma": 10, "wisdom": 10})
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
        "result": "Relationship improved!" if success else "No improvement this time."
    }
