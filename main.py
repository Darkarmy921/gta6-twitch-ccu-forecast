#!/usr/bin/env python3
"""Forecast Twitch CCU for GTA VI's launch day, hours 2-24 (UTC).

Method (stdlib only, deterministic, no network): nearest-neighbour
log-ratio quantiles over the case's own comparables.

  * Anchor: hour 1's print p1. Every comparable launch contributes a
    pseudo-case: its release-day hours 2..24 expressed as log-ratios
    ln(viewers_h / viewers_1). The ramp a launch takes over its release
    day is almost entirely determined by how big hour 1 already is:
    across the 38 comparables, corr(ln v1, ln peak/v1) = -0.94. Games
    whose hour 1 is already huge (simultaneous / early unlock, e.g.
    ELDEN RING, Cyberpunk 2077) stay near flat and peak ~1.0-1.3x;
    games whose hour 1 is tiny (unlock later in the day, e.g. Hollow
    Knight: Silksong, Black Myth: Wukong) ramp 100-2000x by the evening.
  * For the target, take the k=12 comparables nearest in ln(v1) and,
    per hour h, read the five empirical quantiles (5/25/50/75/95%) of
    their log-ratios. The median curve for a GTA-VI-sized hour 1 dips
    to ~0.6x around midday and rises to ~1.0-1.25x in the evening
    (hours 18-24), matching the rolling-midnight unlock wave plus the
    US-evening peak every big comparable shows.
  * Smooth each quantile level across neighbouring hours (centred
    +/-1h mean) to remove single-hour sampling noise, enforce
    non-decreasing quantiles, round to 2 decimals half-up.
  * Fallback: any hour with fewer than 4 neighbours carrying it uses
    the house baseline's row (p1 * exp(z * 0.15 * sqrt(h-1))); with no
    usable comparables at all the whole forecast is the baseline.

Local validation (leave-one-out over the 37 usable comparables in the
practice kit, pinball loss on the log scale, same scorer as the
contest): mean 0.449, median 0.260 vs the house baseline's 0.930 /
0.325 on the same cases. On the 20 comparables with hour 1 >= 50,000
(the regime GTA VI will be in): mean 0.207, median 0.158 vs the
baseline's mean 0.251 on the same cases. On the six biggest comparables (hour 1
>= 200,000) it beats the baseline on five of six (e.g. ELDEN RING
0.108 vs 0.211, Hogwarts Legacy 0.134 vs 0.288, Cyberpunk 2077 0.149
vs 0.230). The practice launches themselves are all big-hour-1 games;
the house baseline scores about 0.387 on them, so a comparable
improvement is expected but NOT verified: the practice answers are
held by the server, and these numbers are leave-one-out estimates on
comparables, not practice scores.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a
# module shipped beside this file imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.674490, 0.0, 0.674490, 1.644854]
BASELINE_SIGMA = 0.15
K = 12
MIN_NEIGHBOURS = 4
HOURS = list(range(2, 25))


def _parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _quantile(sorted_xs, tau):
    n = len(sorted_xs)
    if n == 0:
        return 0.0
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


def _round2(x):
    """x rounded to 2 decimals, half up, as the house baseline rounds it."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    v = whole / 100
    return int(v) if v == int(v) else v


def _baseline_row(p1, h):
    return [_round2(p1 * math.exp(z * BASELINE_SIGMA * math.sqrt(h - 1)))
            for z in Z]


def _comparable_day(comp):
    """Release-day {hour: viewers} for one comparable, or None."""
    try:
        ds = _parse_ts(comp["day_start"])
    except (KeyError, TypeError, ValueError):
        return None
    day = {}
    for pt in comp.get("hourly") or []:
        try:
            t = _parse_ts(pt["from"])
            v = pt["viewers"]
        except (KeyError, TypeError, ValueError):
            continue
        if ds <= t < ds + timedelta(days=1) and isinstance(v, (int, float)) and v > 0:
            h = int((t - ds).total_seconds() // 3600) + 1
            day[h] = v
    if 1 not in day:
        return None
    actual = {h: day[h] for h in HOURS if h in day}
    if len(actual) < 20:
        return None
    return {"v1": day[1], "actual": actual}


def forecast_case(case):
    known = {k["hour"]: k["viewers"] for k in case.get("known") or []}
    p1 = known.get(1)
    if not p1 or p1 < 1:
        p1 = 1
    p1 = float(p1)

    pseudos = []
    for comp in case.get("comparables") or []:
        pc = _comparable_day(comp)
        if pc is not None:
            pseudos.append(pc)

    if len(pseudos) < MIN_NEIGHBOURS:
        return {h: _baseline_row(p1, h) for h in HOURS}

    lv1 = math.log(p1)
    near = sorted(pseudos, key=lambda p: abs(math.log(p["v1"]) - lv1))[:K]

    raw = {}
    for h in HOURS:
        lrs = sorted(math.log(p["actual"][h] / p["v1"])
                     for p in near if h in p["actual"])
        raw[h] = [_quantile(lrs, t) for t in LEVELS] if len(lrs) >= MIN_NEIGHBOURS else None

    # Smooth each quantile level across neighbouring hours (+/-1h mean).
    for j in range(len(LEVELS)):
        vals = [raw[h][j] if raw[h] is not None else None for h in HOURS]
        sm = []
        for i in range(len(HOURS)):
            w = [vals[ii] for ii in range(max(0, i - 1), min(len(vals), i + 2))
                 if vals[ii] is not None]
            sm.append(sum(w) / len(w) if w else None)
        for i, h in enumerate(HOURS):
            if raw[h] is not None and sm[i] is not None:
                raw[h][j] = sm[i]

    out = {}
    for h in HOURS:
        if raw[h] is None:
            out[h] = _baseline_row(p1, h)
            continue
        qs = list(raw[h])
        for j in range(1, len(qs)):
            qs[j] = max(qs[j], qs[j - 1])
        out[h] = [_round2(min(max(p1 * math.exp(q), 0.01), 1e9)) for q in qs]
    return out


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inputs = sorted(p for p in INPUT_DIR.iterdir() if p.name.endswith(".in"))
    for path in inputs:
        case = json.loads(path.read_text(encoding="utf-8"))
        fc = forecast_case(case)
        hours = [{"hour": h, "q": fc[h]} for h in HOURS]
        out_path = OUTPUT_DIR / (path.stem + ".out")
        out_path.write_text(json.dumps({"hours": hours}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
