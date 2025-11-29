"""
OpenWeather API Client

Fetches weather data for demand forecasting.
API Documentation: https://openweathermap.org/api

Falls back to simulation if API key not available.
"""

import requests
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class WeatherAPI:
    """
    Client for OpenWeather API.
    
    Fetches current weather and forecasts. Falls back to simulated
    data if API key not available or API fails.
    """
    
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    # Simulated weather by month (Northern Hemisphere, temperate climate)
    SEASONAL_WEATHER = {
        1: {"temp": 35, "humidity": 70, "conditions": "Cold"},
        2: {"temp": 38, "humidity": 65, "conditions": "Cold"},
        3: {"temp": 48, "humidity": 60, "conditions": "Cool"},
        4: {"temp": 58, "humidity": 55, "conditions": "Mild"},
        5: {"temp": 68, "humidity": 50, "conditions": "Pleasant"},
        6: {"temp": 78, "humidity": 55, "conditions": "Warm"},
        7: {"temp": 85, "humidity": 60, "conditions": "Hot"},
        8: {"temp": 83, "humidity": 65, "conditions": "Hot"},
        9: {"temp": 75, "humidity": 55, "conditions": "Warm"},
        10: {"temp": 62, "humidity": 50, "conditions": "Cool"},
        11: {"temp": 48, "humidity": 60, "conditions": "Cool"},
        12: {"temp": 38, "humidity": 70, "conditions": "Cold"},
    }
    
    def __init__(
        self, 
        api_key: str = None, 
        location: str = "Athens,GR",
        cache_dir: str = None
    ):
        """
        Initialize Weather API client.
        
        Args:
            api_key: OpenWeather API key (or set OPENWEATHER_API_KEY env var)
            location: City,State,Country for weather data
            cache_dir: Directory to cache responses
        """
        self.api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")
        self.location = location
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._last_fetch: Optional[datetime] = None
        self._cached_data: Optional[Dict] = None
        self._previous_temp: Optional[float] = None
        
        if not self.api_key:
            logger.info("No OpenWeather API key found - will use simulated data")
        else:
            logger.info(f"OpenWeather API initialized for {location}")
    
    def get_current_weather(self, target_date: date = None) -> Dict:
        """
        Get current weather data.
        
        Args:
            target_date: Date to get weather for (default: today)
            
        Returns:
            Dict with weather data
        """
        if target_date is None:
            target_date = date.today()
        
        # Try real API if key available
        if self.api_key:
            try:
                data = self._fetch_real_data(target_date)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"Could not fetch real weather data: {e}")
        
        # Fall back to simulation
        logger.info("Using simulated weather data")
        return self._generate_simulated_data(target_date)
    
    def _fetch_real_data(self, target_date: date) -> Optional[Dict]:
        """
        Fetch real weather data from OpenWeather API.
        """
        # Check cache
        if self._cached_data and self._last_fetch:
            cache_age = datetime.now() - self._last_fetch
            if cache_age < timedelta(hours=1):
                logger.debug("Using cached weather data")
                return self._cached_data
        
        try:
            # Current weather endpoint
            url = f"{self.BASE_URL}/weather"
            params = {
                "q": self.location,
                "appid": self.api_key,
                "units": "imperial"  # Fahrenheit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            weather_data = {
                "temperature_avg_f": data["main"]["temp"],
                "temperature_min_f": data["main"]["temp_min"],
                "temperature_max_f": data["main"]["temp_max"],
                "humidity_percent": data["main"]["humidity"],
                "precipitation_probability": 0.0,  # Not in current weather
                "conditions": data["weather"][0]["description"],
                "is_cold_snap": self._detect_cold_snap(data["main"]["temp"]),
                "forecast_date": target_date.isoformat(),
                "data_source": "openweather"
            }
            
            # Update cache
            self._cached_data = weather_data
            self._last_fetch = datetime.now()
            self._previous_temp = data["main"]["temp"]
            
            logger.info(f"Fetched real weather: {weather_data['temperature_avg_f']:.1f}°F")
            return weather_data
            
        except Exception as e:
            logger.error(f"OpenWeather API error: {e}")
            return None
    
    def _generate_simulated_data(self, target_date: date) -> Dict:
        """
        Generate realistic simulated weather data.
        """
        import random
        
        month = target_date.month
        base = self.SEASONAL_WEATHER[month]
        
        # Add daily variation
        temp_variation = random.uniform(-8, 8)
        avg_temp = base["temp"] + temp_variation
        
        # Min/max temperatures
        temp_range = random.uniform(10, 20)
        min_temp = avg_temp - temp_range / 2
        max_temp = avg_temp + temp_range / 2
        
        # Humidity variation
        humidity = base["humidity"] + random.uniform(-10, 10)
        humidity = max(20, min(95, humidity))
        
        # Precipitation probability
        precip_prob = random.uniform(0, 0.4) if humidity > 60 else random.uniform(0, 0.2)
        
        # Detect cold snap
        is_cold_snap = False
        if self._previous_temp is not None:
            temp_drop = self._previous_temp - avg_temp
            is_cold_snap = temp_drop > 15  # 15°F drop
        self._previous_temp = avg_temp
        
        # Conditions
        if precip_prob > 0.6:
            if avg_temp < 32:
                conditions = "Snow likely"
            else:
                conditions = "Rain likely"
        elif avg_temp < 32:
            conditions = "Cold and clear"
        elif avg_temp > 85:
            conditions = "Hot and humid"
        else:
            conditions = base["conditions"]
        
        return {
            "temperature_avg_f": round(avg_temp, 1),
            "temperature_min_f": round(min_temp, 1),
            "temperature_max_f": round(max_temp, 1),
            "humidity_percent": round(humidity, 1),
            "precipitation_probability": round(precip_prob, 2),
            "conditions": conditions,
            "is_cold_snap": is_cold_snap,
            "forecast_date": target_date.isoformat(),
            "data_source": "simulated"
        }
    
    def _detect_cold_snap(self, current_temp: float) -> bool:
        """Detect if there's a sudden temperature drop."""
        if self._previous_temp is None:
            return False
        
        temp_drop = self._previous_temp - current_temp
        return temp_drop > 15  # 15°F drop is significant