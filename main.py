# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello, world!"}

@app.get("/astro")
def astro(name: str = "Moon"):
    # your Swiss Ephemeris / astrology calculation code
    return {"name": name, "rashi": "Aries", "nakshatra": "Anuradha"}
