# LinkedIn post draft — Recall Blast Radius

> **Draft only — not posted.** Review, attach a screen capture of the
> Scenario B graph (the shared-ingredient fan-out at recall.lailarallc.com,
> "Scenario B" tab), and post manually. Figures below are verified against
> the scenario cache (`pipeline/cache/scenario_graphs.json`), 2026-07-13.

---

It's 2pm on a Friday. Your supplier just called: one ingredient lot failed a pathogen test.

How bad this gets is already decided — it was decided months ago, every time your co-manufacturer drew from the same pallet of chili flakes for another production run.

I modeled this on a synthetic $25M specialty food brand:

Scenario A — the lot went into one production run. A contained, documented retrieval.

Scenario B — the same lot fed 23 production batches. 23 affected lots. 14 SKUs across two product lines. 6 retailers to notify. 5,785 cases still in channel. That's 47.8× the blast radius of Scenario A, from one shared ingredient lot.

The cost gap is the whole story. Targeted retrieval in Scenario B: $52K–$81K. A full recall, because you can't prove which lots are clean: $10M+ — against roughly $2.75M of annual EBITDA. Three-plus years of earnings, gone on the difference between knowing and guessing.

The difference between A and B isn't ingredient risk. It's whether the batch genealogy exists when the phone rings. FSMA 204 is about to make that record-keeping non-optional for a long list of foods.

I built an interactive version — trace any lot forward and watch the blast radius draw itself: https://recall.lailarallc.com

---

*Alt text for the screen capture: "Network graph showing one ingredient lot fanning out through 23 production batches into 14 SKUs, ending at 6 retailers — 5,785 cases in channel."*
