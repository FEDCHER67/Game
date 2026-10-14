---
name: grill-me
description: "Interview the user relentlessly about a plan or design (for example the game map) until every open decision is settled, then write a complete spec. Use when the user says grill me, допроси меня, погриль, or asks to build a full spec together."
---

# Grill me

Goal: turn a vague idea into a spec with no open questions, by interviewing the user.

How to run it:
1. Read what already exists first (repo docs, plans, reports) so you never ask what the files already answer. For the VOLUNTEERS ONLY map, read ArtSource/References/Map/MAP_PLAN_R01_v18_REPORT.md, the newest map plan report, docs/PRODUCT.md and docs/ArtDirection.md if present.
2. Build a decision tree: list every decision the spec needs (purpose, scale, districts, roads, landmarks, gameplay points, look, constraints, priorities). Resolve dependencies top-down.
3. Ask ONE question at a time, in the user's language (Russian for Fedya), short and concrete. For each question give your recommended answer and 2-3 alternatives with the trade-off, so the user can reply with a letter or one word.
4. Push back on vague or contradictory answers; ask a follow-up until the answer is testable (numbers, names, places).
5. Keep a running list of settled decisions; every ~5 questions show a short recap and what is still open.
6. Stop only when nothing important is open or the user says enough. Then write the spec as a Markdown file (for the map: docs/specs/MAP_SPEC_<date>.md): goals, settled decisions, numbers, per-area details, acceptance checks, and the still-open items marked clearly.

Never invent answers on the user's behalf; if they skip a question, record it as open.
