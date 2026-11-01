# Back-test: Replay: Cyclone Titli, Oct 2018

> Scenario data are illustrative reconstructions; these numbers test the pipeline, not real-world skill.

Risk config v1 · 13 blocks reported affected

| Metric (PRD §2.3) | Result | Target |
|---|---|---|
| Recall of affected blocks (alerted, High+) | 85% (11/13) | ≥ 80% |
| False alarm rate of Severe alerts | 0% (0/5) | ≤ 25% |
| Median lead time of Severe warning | +6 h | ≥ 6 h |

| Threshold | Recall | False alarm rate | Median lead h | Missed | False alarms |
|---|---|---|---|---|---|
| High (≥55) | 85% | 0% | +9 | digapahandi, sorada | — |
| Severe (≥75) | 38% | 0% | +6 | aska, digapahandi, hinjilicut, kabisuryanagar, kukudakhandi, polasara, rangeilunda, sorada | — |

Times are hours relative to landfall.

| Block | Peak | Level | Peak t | Affected | Impact t | High warned | Severe warned | Severe lead h |
|---|---|---|---|---|---|---|---|---|
| Ganjam | 98 | Severe | +10 | yes | +10 | -8 | -2 | +12 |
| Patrapur | 89 | Severe | +2 | yes | +2 | -8 | -4 | +6 |
| Purushottampur | 86 | Severe | +2 | yes | +8 | -12 | -7 | +15 |
| Chikiti | 79 | Severe | +3 | yes | +2 | -7 | +0 | +2 |
| Sanakhemundi | 77 | Severe | +3 | yes | +4 | -6 | +1 | +3 |
| Aska | 68 | High | +3 | yes | +8 | -9 | — | — |
| Rangeilunda | 68 | High | +8 | yes | +2 | -5 | — | — |
| Hinjilicut | 66 | High | +7 | yes | +6 | -2 | — | — |
| Kabisuryanagar | 64 | High | +12 | yes | +8 | +1 | — | — |
| Polasara | 63 | High | +10 | yes | +10 | +7 | — | — |
| Kukudakhandi | 58 | High | +7 | yes | +3 | -3 | — | — |
| Digapahandi | 49 | Moderate | +8 | yes | +4 | — | — | — |
| Buguda | 37 | Moderate | +8 | no | — | — | — | — |
| Chhatrapur | 28 | Low | +9 | no | — | — | — | — |
| Khallikote | 22 | Low | +12 | no | — | — | — | — |
| Sorada | 22 | Low | +10 | yes | +10 | — | — | — |
| Beguniapada | 18 | Low | +11 | no | — | — | — | — |
| Sheragada | 18 | Low | +7 | no | — | — | — | — |
| Dharakote | 15 | Low | +9 | no | — | — | — | — |
| Jagannathprasad | 12 | Low | +9 | no | — | — | — | — |
| Bellaguntha | 11 | Low | +10 | no | — | — | — | — |
| Bhanjanagar | 11 | Low | +9 | no | — | — | — | — |
