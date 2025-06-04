from fastapi import FastAPI
import random

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.get("/roll_dice")
def roll_dice(sides: int = 20):
    return {"result": random.randint(1, sides)}
