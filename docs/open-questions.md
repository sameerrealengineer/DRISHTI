# Open questions

From PRD §20, plus items found while building.

## From the PRD

- Official MPCS (cyclone shelter) list for Ganjam — `seed/shelters.json` is sample data.
- Team rosters and codes from DEOC — `seed/teams.json` is demo data.
- Preferred SMS gateway (MSG91 / Gupshup / Twilio India) and DLT registration.
- Hosting: State Data Centre vs. cloud.
- Pilot blocks confirmation (proposed: Purushottampur, Aska, Rangeilunda).

## Found during M0–M2

- **Reference prototype missing.** `reference/prototype/` (index.html, model.js, engine.js) and the
  prototype's seed/scenario files were not in the repository. Seed values were estimated and the Titli
  scenario was tuned to reproduce the M2 DoD scores. Please add the prototype so the web UI (M8) can
  match it and the seed data can be swapped for the original.
- **Block attributes.** Centroids, elevation, population and kutcha share in `seed/blocks.json` are rough
  estimates. Need SRTM means and Census 2011 figures per block.
- **Gauge danger levels.** Only Rushikulya @ Purushottampur (16.83 m) is sourced. Bahuda @ Sunapur,
  Ghodahada @ Digapahandi and Badanadi @ Aska are placeholders to confirm with CWC.
- **Ground truth.** The affected-block lists and impact hours in `seed/scenarios/*.ground_truth.json`
  are illustrative; verify against OSDMA damage reports for Titli and Phailin.
- **Odia strings needing native review:** all `name_or` block names in `seed/blocks.json`; Odia report
  texts in `scripts/gen_scenarios.py`.
- **Early-warning KPI vs. demo script.** BE-FC-3 says the KPI shows the area with the earliest
  hours-to-severe; in the Titli replay that is Purushottampur (from −7 h). The demo script (§19.2) says
  "Patrapur in N h". Patrapur does appear as the early-warning *alert candidate* (BE-FC-2) at −4 h.
  Implemented per BE-FC-3; confirm which the pitch should show.
- **Surge forecasting.** v1 forecast holds satellite flood constant, so Phailin's surge is warned about
  1 h after impact (see `reports/backtest_phailin.md`).
- **LICENSE.** The PRD lists a LICENSE file but not which license. Choose one (e.g. MIT or Apache-2.0).
