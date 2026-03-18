import time
import warnings

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import SSLError
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry


class WeatherService:
    """
    Free weather service using Open-Meteo (no API key)
    """

    CACHE_TTL = 60 * 60 * 3   # 3 hours
    DEFAULT_WEATHER = {
        "temp_max": 25,
        "humidity": 60,
        "rain_prob": 0,
        "rain_mm": 0.0,
    }

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        self._cache = None
        self._cache_time = 0

        self._session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

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

            # Use stale cache if available instead of dropping to defaults.
            if self._cache is not None:
                return self._cache

            # FAIL SAFE (do NOT overwater)
            return dict(self.DEFAULT_WEATHER)

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

        r = self._request_json(url, params=params)
        data = r

        daily = data["daily"]

        return {
            "temp_max": self._safe_int(
                self._pick_first(daily.get("temperature_2m_max")),
                self.DEFAULT_WEATHER["temp_max"],
            ),
            "humidity": self._safe_int(
                self._pick_first(daily.get("relative_humidity_2m_max")),
                self.DEFAULT_WEATHER["humidity"],
            ),
            "rain_prob": self._safe_int(
                self._pick_first(daily.get("precipitation_probability_max")),
                self.DEFAULT_WEATHER["rain_prob"],
            ),
            "rain_mm": self._safe_float(
                self._pick_first(daily.get("precipitation_sum")),
                self.DEFAULT_WEATHER["rain_mm"],
            ),
        }

    def _request_json(self, url: str, params: dict) -> dict:
        try:
            resp = self._session.get(url, params=params, timeout=12)
            resp.raise_for_status()
            return resp.json()
        except SSLError:
            # Fallback for environments that fail TLS handshake with Open-Meteo.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InsecureRequestWarning)
                resp = self._session.get(
                    url,
                    params=params,
                    timeout=12,
                    verify=False,
                )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _pick_first(values):
        if isinstance(values, list) and values:
            return values[0]
        return None

    @staticmethod
    def _safe_int(value, default: int) -> int:
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _safe_float(value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)
