#!/usr/bin/env python3
"""Morning sport advisor. Python stdlib only.

Fetches forecasts (Open-Meteo, MeteoSwiss ICON-CH where available),
decides which sports are feasible today, compares with the previous day,
and writes result.json. The iPhone Shortcut only reads result.json.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Zurich")
ROOT = Path(__file__).parent
RESULT = ROOT / "result.json"
STATE = ROOT / "state.json"

# ---------------------------------------------------------------- locations
# (lat, lon, elevation_m or None). VERIFY Champery coords on a map.
NYON = (46.383, 6.239, None)
CHAMPERY = (46.170, 6.860, 1960)  # Croix de Culet, approx.

# --------------------------------------------------------------- thresholds
WINDOW = 3                      # consecutive hours required (bike, sail)
RAIN_MM = 0.1                   # hourly precip below this = dry

BIKE_HOURS = range(8, 21)       # slots 08:00..20:00 -> ends by 21:00
BIKE_MAX_WIND_KN = 12           # was <5; 12 kn ~ 22 km/h, still comfortable
BIKE_MIN_TEMP_C = 8

SAIL_HOURS = range(8, 21)
SAIL_MIN_WIND_KN = 15
SAIL_MAX_WIND_KN = 35
SAIL_MIN_AIR_C = 20
SAIL_MIN_WATER_C = 15

SKI_MIN_SNOW_CM = 30
SUNNY_HOURS = range(8, 20)      # 08:00..20:00
SUNNY_MAX_CLOUD_PCT = 30
SKI_SNOW_HOUR = 12              # snow depth read at noon

# Approx. Lake Geneva surface temp by month (deg C). ESTIMATE, not measured.
# Override with env var WATER_TEMP_C, or replace get_water_temp() with a real source.
WATER_BY_MONTH = {1: 6, 2: 5.5, 3: 6, 4: 8, 5: 12, 6: 17,
                  7: 21, 8: 22, 9: 19, 10: 15, 11: 11, 12: 8}


def get_water_temp(month):
    override = os.environ.get("WATER_TEMP_C")
    return float(override) if override else float(WATER_BY_MONTH[month])


def fetch(lat, lon, elevation=None):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,cloud_cover,snow_depth",
        "wind_speed_unit": "kn",
        "timezone": "Europe/Zurich",
        "forecast_days": 1,
    }
    if elevation:
        params["elevation"] = elevation
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    with urlopen(url, timeout=30) as r:
        return json.load(r)["hourly"]


def g(d, key, h):
    """Hourly value or NaN (NaN fails every comparison -> condition false)."""
    x = d[key][h]
    return float("nan") if x is None else float(x)


def first_window(hours, ok):
    hs = list(hours)
    for i in range(len(hs) - WINDOW + 1):
        if all(ok(h) for h in hs[i:i + WINDOW]):
            return hs[i]
    return None


def evaluate(nyon, champ, water_c):
    """Return {sport: one-line weather summary} for feasible sports."""
    out = {}

    # BIKE: dry + calm + warm, 3 consecutive hours
    def bike_ok(h):
        return (g(nyon, "precipitation", h) < RAIN_MM
                and g(nyon, "wind_speed_10m", h) < BIKE_MAX_WIND_KN
                and g(nyon, "temperature_2m", h) > BIKE_MIN_TEMP_C)

    s = first_window(BIKE_HOURS, bike_ok)
    if s is not None:
        hrs = range(s, s + WINDOW)
        w = max(g(nyon, "wind_speed_10m", h) for h in hrs)
        t = min(g(nyon, "temperature_2m", h) for h in hrs)
        out["bike"] = f"Bike, Nyon: from {s}h, {t:.0f} degrees, wind {w:.0f} knots, dry"

    # SAIL: wind band + warm air + warm water, 3 consecutive hours
    def sail_ok(h):
        return (SAIL_MIN_WIND_KN <= g(nyon, "wind_speed_10m", h) <= SAIL_MAX_WIND_KN
                and g(nyon, "temperature_2m", h) >= SAIL_MIN_AIR_C)

    if water_c >= SAIL_MIN_WATER_C:
        s = first_window(SAIL_HOURS, sail_ok)
        if s is not None:
            hrs = range(s, s + WINDOW)
            w = min(g(nyon, "wind_speed_10m", h) for h in hrs)
            t = min(g(nyon, "temperature_2m", h) for h in hrs)
            out["sail"] = (f"Sailing, Nyon: from {s}h, wind {w:.0f} knots, "
                           f"air {t:.0f}, water about {water_c:.0f}")

    # SKI: >=30 cm and mean cloud cover <30% over 08-20h
    snow_cm = g(champ, "snow_depth", SKI_SNOW_HOUR) * 100
    clouds = [g(champ, "cloud_cover", h) for h in SUNNY_HOURS]
    cloud = sum(clouds) / len(clouds)
    if snow_cm >= SKI_MIN_SNOW_CM and cloud < SUNNY_MAX_CLOUD_PCT:
        out["ski"] = f"Ski, Champery: {snow_cm:.0f} cm snow, clouds {cloud:.0f} percent"

    return out


def load(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main():
    now = datetime.now(TZ)
    today = now.date().isoformat()
    force = os.environ.get("FORCE") == "1"
    state = load(STATE)

    if not force:
        if now.hour < 5:
            print("before 05:00 local, skip")
            return
        if state and state.get("date") == today:
            print("already done today, skip")
            return

    try:
        nyon = fetch(*NYON)
        champ = fetch(*CHAMPERY)
        found = evaluate(nyon, champ, get_water_temp(now.month))
    except Exception as e:  # network/API failure: report once, keep state
        write(RESULT, {"date": today, "changed": True, "sports": [],
                       "message": f"Weather check failed: {e}"})
        return

    sports = sorted(found)
    # yesterday = last stored set (or the stored 'yesterday' if re-run today)
    if state is None:
        yesterday = None
    elif state.get("date") == today:
        yesterday = state.get("yesterday")
    else:
        yesterday = state.get("sports")

    changed = yesterday is None or set(sports) != set(yesterday)
    if not changed:
        message = ""
    elif sports:
        message = ". ".join(found[s] for s in sports)
    else:
        message = "No sport possible today."

    write(STATE, {"date": today, "sports": sports, "yesterday": yesterday})
    write(RESULT, {"date": today, "changed": changed, "sports": sports,
                   "message": message})
    print(json.dumps({"sports": sports, "changed": changed, "message": message}))


if __name__ == "__main__":
    main()
