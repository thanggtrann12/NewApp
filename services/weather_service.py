import time
import requests


class WeatherService:
    """
    Free weather service using Open-Meteo (no API key)
    """

    CACHE_TTL = 60 * 60 * 3   # 3 hours

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        self._cache = None
        self._cache_time = 0

    # ==================================================
    def get_today(self) -> dict:
        if self._is_cache_valid():
            return self._cache

        try:
            weather = self._fetch_and_parse()
            self._cache = weather
            self._cache_time = time.time()
            return weather

        except Exception as e:
            print(f"[WeatherService] error: {e}")

            # FAIL SAFE (do NOT overwater)
            return {
                "temp_max": 25,
                "humidity": 60,
                "rain_prob": 0,
                "rain_mm": 0
            }

    # ==================================================
    def _is_cache_valid(self) -> bool:
        return (
            self._cache is not None and
            time.time() - self._cache_time < self.CACHE_TTL
        )

    # ==================================================
    def _fetch_and_parse(self) -> dict:
        url = "https://api.open-meteo.com/v1/forecast"

        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "daily": (
                "temperature_2m_max,"
                "precipitation_probability_max,"
                "precipitation_sum,"
                "relative_humidity_2m_max"
            ),
            "timezone": "auto"
        }

        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        daily = data["daily"]

        return {
            "temp_max": int(daily["temperature_2m_max"][0]),
            "humidity": int(daily["relative_humidity_2m_max"][0]),
            "rain_prob": int(daily["precipitation_probability_max"][0]),
            "rain_mm": float(daily["precipitation_sum"][0])
        }
