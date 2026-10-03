# morning-advisor

Alarm stopped -> iPhone speaks which sports are feasible today, only if the set changed vs yesterday.

```
GitHub Actions (05:00 Zurich) -> decide.py -> result.json (+ state.json)
iPhone alarm "Is Stopped" -> Shortcut -> GET result.json -> speak "message" if not empty
```

## Setup
1. Create a GitHub repo (public: raw URL needs no token), push this folder as-is.
2. Repo > Settings > Actions > General > Workflow permissions: allow read and write.
3. Actions tab > morning-advisor > Run workflow (forced run). Check result.json is committed.
4. Raw URL: https://raw.githubusercontent.com/<user>/<repo>/main/result.json

## iPhone Shortcut
Shortcuts > Automation > New > Alarm > Is Stopped (choose your alarm) > Run Immediately.
Actions:
1. Get Contents of URL (raw URL above)
2. Get Dictionary from Input
3. Get Dictionary Value: `message`
4. If `Dictionary Value` has any value -> Speak Text (Dictionary Value)

## Tune
All thresholds are constants at the top of `decide.py`.
Local test: `FORCE=1 python3 decide.py`; set `WATER_TEMP_C=17` to override water temp.

## Known weak points
- Water temp = monthly estimate table, not a measurement.
- Champery coordinates approximate; verify on a map.
- Model snow depth at altitude is crude; cross-check with a real snow report.
- First run has no history, so it always speaks.
