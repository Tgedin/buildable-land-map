# Discovery call: script (20 min)

Goal: learn how they look for land today and whether this map changes a decision. Do not pitch. Do not defend the numbers.

**Before:** open https://tgedin.github.io/buildable-land-map/ on the device you will share. Have `docs/discovery/README.md` open for the template. Ask permission to take notes; log role and learnings only, no names.

| Min | Step | Say / ask |
|---|---|---|
| 0–2 | Frame | "I'm testing a map of unused building height in Ruzafa. I want to hear how you actually work, not sell you anything." |
| 2–8 | Today (map closed) | How did you find the last plot or building you looked at? What did you lack, and how long did it take? Who did you ask? |
| 8–10 | Show | Share the link. Say nothing about what it means. |
| 10–16 | First reaction | What do you click first? What do you expect it to show? Read the legend aloud: what does "missing floors" mean to you? Point at a parcel you know: is the number plausible? |
| 16–19 | Trust | What would you need to trust this number? What would make it useless? What is missing (zoning, ownership, price, use)? |
| 19–20 | Close | Would you share it? With whom? Can I ask you to try it again in two weeks? |

**Things to listen for** (these are the open questions in the repo):
- Do they read "gap" as *buildable*? (It is not zoning. The footer says so; do they see it?)
- Do public buildings, schools, markets and protected buildings show up as false hope? (ADR 0003 known weakness.)
- Do they care about floors accuracy (M2: 86% within ±1) or about zoning and ownership instead? This decides whether more LiDAR work is worth it.
- What would they filter by first?

**After:** write the note the same day using the template. Under "One change to make", write one concrete change, and put the note's filename in the commit message that implements it (M3 Must).
