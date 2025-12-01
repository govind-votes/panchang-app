from fastapi import FastAPI, Query, HTTPException
from .astrology import get_planet_positions

app = FastAPI(title="Astrology API")

@app.get("/astro")
def astro(
    year: int = Query(...),
    month: int = Query(...),
    day: int = Query(...),
    hour: float = Query(..., description="Decimal hour, e.g., 8.49"),
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    try:
        data = get_planet_positions(year, month, day, hour, lat, lon)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
