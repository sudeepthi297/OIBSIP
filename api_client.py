"""API Client for fetching weather data and user IP-based location."""

import os
from typing import Any, Dict, Optional, Tuple
import requests


class WeatherAPIError(Exception):
    """Custom exception class for Weather API errors."""
    pass


class WeatherAPIClient:
    """Client for interacting with OpenWeatherMap and IPInfo APIs."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    ICON_URL = "https://openweathermap.org/img/wn/{icon_code}@2x.png"
    IPINFO_URL = "https://ipinfo.io/json"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize API Client.

        Args:
            api_key: OpenWeatherMap API key. If not provided, reads from environment.
        """
        self.api_key = api_key or "3433d640e8e07a966b27357d0c607abd"
        if not self.api_key:
            raise ValueError("OpenWeatherMap API Key is missing. Set OPENWEATHER_API_KEY environment variable.")

    def get_auto_location(self) -> Tuple[str, str]:
        """Fetch city and country based on user's public IP address.

        Returns:
            Tuple containing (city_name, country_code).
        """
        try:
            response = requests.get(self.IPINFO_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("city", ""), data.get("country", "")
        except requests.RequestException as e:
            raise WeatherAPIError(f"Failed to detect location automatically: {e}")

    def fetch_current_weather(self, query: str) -> Dict[str, Any]:
        """Fetch current weather data for a given city or ZIP code.

        Args:
            query: City name or ZIP code.

        Returns:
            Parsed JSON dictionary of current weather.
        """
        url = f"{self.BASE_URL}/weather"
        params = {"q": query, "appid": self.api_key, "units": "metric"}
        return self._make_request(url, params)

    def fetch_forecast(self, query: str) -> Dict[str, Any]:
        """Fetch 5-day / 3-hour forecast data.

        Args:
            query: City name or ZIP code.

        Returns:
            Parsed JSON dictionary of forecast data.
        """
        url = f"{self.BASE_URL}/forecast"
        params = {"q": query, "appid": self.api_key, "units": "metric"}
        return self._make_request(url, params)

    def fetch_icon_bytes(self, icon_code: str) -> bytes:
        """Download raw bytes for a weather icon.

        Args:
            icon_code: OpenWeatherMap icon code string (e.g., '10d').

        Returns:
            Raw image byte array.
        """
        url = self.ICON_URL.format(icon_code=icon_code)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            return b""  # Return empty bytes on image fetch failure

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to handle HTTP requests and translate error codes."""
        try:
            response = requests.get(url, params=params, timeout=8)
            
            if response.status_code == 401:
                raise WeatherAPIError("Invalid OpenWeatherMap API Key.")
            elif response.status_code == 404:
                raise WeatherAPIError("Location not found. Please check spelling.")
            
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise WeatherAPIError("Request timed out. Check your internet connection.")
        except requests.exceptions.ConnectionError:
            raise WeatherAPIError("Network error. Unable to connect to weather service.")
        except requests.RequestException as e:
            raise WeatherAPIError(f"API Error: {str(e)}")