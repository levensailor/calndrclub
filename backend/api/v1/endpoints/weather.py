from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx

from core.security import get_current_user
from core.logging import logger
from schemas.weather import WeatherAPIResponse
from services.weather_service import get_cache_key, get_cached_weather, cache_weather_data

router = APIRouter()

@router.get("/{latitude}/{longitude}", response_model=WeatherAPIResponse)
async def get_weather(
    latitude: float, 
    longitude: float, 
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    temperature_unit: Optional[str] = Query("celsius", description="Temperature unit (celsius or fahrenheit)"),
    current_user = Depends(get_current_user)
):
    """
    Fetches weather forecast data.
    """
    logger.info(f"Fetching weather for lat={latitude}, lon={longitude} from {start_date} to {end_date}")
    
    # --- Caching ---
    cache_key = get_cache_key(latitude, longitude, start_date, end_date, f"forecast-{temperature_unit}")
    cached_data = await get_cached_weather(cache_key)
    if cached_data:
        logger.info("Returning cached forecast weather data.")
        return cached_data

    # --- API Call ---
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,precipitation_probability_mean,cloudcover_mean",
        "timezone": "auto",
        "temperature_unit": temperature_unit
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            
            # Cache the new data
            await cache_weather_data(cache_key, weather_data, "forecast")
            
            return weather_data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching weather data: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch weather data")
    except httpx.RequestError as e:
        logger.error(f"Request error fetching weather data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while communicating with the weather service")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching weather data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/historic/{latitude}/{longitude}", response_model=WeatherAPIResponse)
async def get_historic_weather(
    latitude: float, 
    longitude: float, 
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    temperature_unit: Optional[str] = Query("celsius", description="Temperature unit (celsius or fahrenheit)"),
    current_user = Depends(get_current_user)
):
    """
    Fetches historic weather data.
    """
    logger.info(f"Fetching historic weather for lat={latitude}, lon={longitude} from {start_date} to {end_date}")

    # --- Caching ---
    cache_key = get_cache_key(latitude, longitude, start_date, end_date, f"historic-{temperature_unit}")
    cached_data = await get_cached_weather(cache_key)
    if cached_data:
        logger.info("Returning cached historic weather data.")
        return cached_data

    # --- API Call ---
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,precipitation_probability_mean,cloudcover_mean",
        "timezone": "auto",
        "temperature_unit": temperature_unit
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            weather_data = response.json()

            # Cache the new data
            await cache_weather_data(cache_key, weather_data, "historic")

            return weather_data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching historic weather data: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch historic weather data")
    except httpx.RequestError as e:
        logger.error(f"Request error fetching historic weather data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while communicating with the weather service")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching historic weather data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
