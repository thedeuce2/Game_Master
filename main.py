from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import random

app = FastAPI()

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
    # Example buff logic: give a bonus to STR for "Half-Orc", DEX for "Elf", etc.
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
    # Hit points: just 8 + CON for this demo
    hp = 8 + ((stats["constitution"] - 10) // 2)
    return {
        "name": request.name,
        "background": request.background,
        "race": request.race,
        "stats": stats,
        "hp": hp,
        "buffs": buffs
    }

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.get("/roll_dice")
def roll_dice(sides: int = 20):
    return {"result": random.randint(1, sides)}
