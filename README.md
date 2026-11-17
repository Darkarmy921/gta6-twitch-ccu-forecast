# gta6-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Darkarmy921/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Darkarmy921/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Nearest-neighbour log-ratio quantile forecaster for GTA VI's launch-day Twitch CCU, hours 2–24 (UTC). For each hour it reads the five empirical quantiles of that hour's log-ratio to hour 1 across the 12 past launches in the case's comparables nearest in hour-1 size, then smooths each quantile level across neighbouring hours. The ramp a launch takes over its release day is almost entirely determined by how big hour 1 already is (corr −0.94 across the comparables), so anchoring on hour-1 size — not on a flat persistence median — is what beats the house baseline. Python 3.13, standard library only, no network, deterministic.

Leave-one-out over the 37 usable comparables in the practice kit (pinball loss on the log scale): mean 0.449, median 0.260 vs the house baseline's 0.930 / 0.325. On the 20 comparables with hour 1 ≥ 50,000 (the regime GTA VI will be in): mean 0.207, median 0.158 vs the baseline's 0.251. The practice answers are held by the server, so these are leave-one-out estimates on comparables, not practice scores.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=ppee1fs7&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
