# morning-advisor
###This project's goal is to automatically suggest to me which sports are possible to do today.  when i turn off the alarm in the morning the automation start and tells me the weather, the wind or the snow depth depending on the sport that is possible to do.
Alarm stopped -> iPhone speaks which sports are feasible today, only if the set changed vs yesterday.

```
GitHub Actions (05:00 Zurich) -> decide.py -> result.json (+ state.json)
iPhone alarm "Is Stopped" -> Shortcut -> GET result.json -> speak "message" if not empty
```
## Known weak points
- Water temp = monthly estimate table, not a measurement.
- Champery coordinates approximate; verify on a map.
- Model snow depth at altitude is crude; cross-check with a real snow report.
- First run has no history, so it always speaks.
