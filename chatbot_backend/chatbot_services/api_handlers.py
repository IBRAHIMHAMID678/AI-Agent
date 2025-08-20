# chatbot_services/api_handlers.py

import httpx
import time
import re
import asyncio 

WEATHER_CACHE = {}
WEATHER_CACHE_TTL_SECONDS = 300  # 5 minutes

WEATHER_DESCRIPTIONS = {
    0: "clear sky ☀️", 1: "mainly clear 🌤", 2: "partly cloudy ⛅", 3: "overcast ☁️",
    45: "fog 🌫", 48: "depositing rime fog ❄️", 51: "light drizzle 🌦",
    53: "moderate drizzle 🌦", 55: "dense drizzle 🌧", 61: "light rain 🌧",
    63: "moderate rain 🌧", 65: "heavy rain 🌧", 71: "light snow 🌨",
    73: "moderate snow 🌨", 75: "heavy snow ❄️", 95: "thunderstorm ⛈",
    96: "thunderstorm with hail ⛈",
}

def get_weather_description(code):
    return WEATHER_DESCRIPTIONS.get(code, "unknown weather 🌍")

async def get_coordinates_async(city):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city, "count": 1}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            results = response.json().get("results")
            if not results:
                return None, None
            result = results[0]
            return result["latitude"], result["longitude"]
    except Exception as e:
        print(f"⚠️ Error fetching coordinates for {city}: {e}")
        return None, None

async def show_weather_api_async(city: str) -> dict:
    """
    Fetches weather data asynchronously for a given city.
    This function should be called directly by the LangChain tool.
    """
    if not city:
        return {"status": "error", "message": "🌍 Please provide a city name."}

    city_key = city.lower().strip()
    current_time = time.time()

    cached = WEATHER_CACHE.get(city_key)
    if cached and current_time - cached["timestamp"] < WEATHER_CACHE_TTL_SECONDS:
        print(f"DEBUG: Serving weather for {city.title()} from cache.")
        return {"status": "success", "message": cached["message"]}

    lat, lon = await get_coordinates_async(city)
    if lat is None or lon is None:
        return {"status": "error", "message": "⚠️ Could not find the city."}

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": True}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            weather = response.json().get("current_weather")

        if not weather:
            return {"status": "error", "message": "⚠️ Weather data not available."}

        temp = weather["temperature"]
        code = weather["weathercode"]
        description = get_weather_description(code)
        message = f"🌤 It is {temp}°C and {description} in {city.title()}."

        WEATHER_CACHE[city_key] = {"message": message, "timestamp": current_time}
        return {"status": "success", "message": message}

    except Exception as e:
        if cached:
            print(f"WARNING: API call failed. Serving expired cache. Error: {e}")
            return {"status": "success", "message": cached["message"]}
        return {"status": "error", "message": f"⚠️ Error fetching weather data: {e}"}

