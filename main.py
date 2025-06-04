from fastapi import FastAPI
import random
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Character(BaseModel):
    name: str
    background: Optional[str] = None
    level: int = 1
    stats: dict
    hp: int
    inventory: Optional[list] = []

@app.post("/create_character")
def create_character(character: Character):
    # You can expand this to auto-generate HP, stats, etc., if needed
    return {"character": character}


@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.get("/roll_dice")
def roll_dice(sides: int = 20):
    return {"result": random.randint(1, sides)}
