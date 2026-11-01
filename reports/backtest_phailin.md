# Back-test: Replay: Cyclone Phailin, Oct 2013

> Scenario data are illustrative reconstructions; these numbers test the pipeline, not real-world skill.

Risk config v1 · 13 blocks reported affected

| Metric (PRD §2.3) | Result | Target |
|---|---|---|
| Recall of affected blocks (alerted, High+) | 46% (6/13) | ≥ 80% |
| False alarm rate of Severe alerts | 0% (0/3) | ≤ 25% |
| Median lead time of Severe warning | -1 h | ≥ 6 h |

| Threshold | Recall | False alarm rate | Median lead h | Missed | False alarms |
|---|---|---|---|---|---|
| High (≥55) | 46% | 0% | +2.5 | beguniapada, chikiti, digapahandi, hinjilicut, kabisuryanagar, patrapur, polasara | — |
| Severe (≥75) | 23% | 0% | -1 | beguniapada, chikiti, digapahandi, hinjilicut, kabisuryanagar, khallikote, kukudakhandi, patrapur, polasara, purushottampur | — |

Times are hours relative to landfall.

| Block | Peak | Level | Peak t | Affected | Impact t | High warned | Severe warned | Severe lead h |
|---|---|---|---|---|---|---|---|---|
| Ganjam | 100 | Severe | +1 | yes | +0 | -12 | -3 | +3 |
| Chhatrapur | 81 | Severe | +4 | yes | +0 | -6 | +1 | -1 |
| Rangeilunda | 81 | Severe | +10 | yes | +0 | -11 | +1 | -1 |
| Khallikote | 64 | High | +13 | yes | +1 | +5 | — | — |
| Purushottampur | 64 | High | +11 | yes | +3 | +4 | — | — |
| Kukudakhandi | 58 | High | +11 | yes | +1 | +7 | — | — |
| Patrapur | 47 | Moderate | +10 | yes | +2 | — | — | — |
| Chikiti | 41 | Moderate | +10 | yes | +2 | — | — | — |
| Hinjilicut | 41 | Moderate | +11 | yes | +3 | — | — | — |
| Kabisuryanagar | 38 | Moderate | +12 | yes | +3 | — | — | — |
| Polasara | 37 | Moderate | +11 | yes | +3 | — | — | — |
| Beguniapada | 31 | Moderate | +4 | yes | +2 | — | — | — |
| Aska | 27 | Low | +12 | no | — | — | — | — |
| Digapahandi | 26 | Low | +11 | yes | +3 | — | — | — |
| Sanakhemundi | 26 | Low | +12 | no | — | — | — | — |
| Buguda | 22 | Low | +13 | no | — | — | — | — |
| Sheragada | 21 | Low | +3 | no | — | — | — | — |
| Sorada | 18 | Low | +6 | no | — | — | — | — |
| Dharakote | 16 | Low | +5 | no | — | — | — | — |
| Bellaguntha | 15 | Low | +5 | no | — | — | — | — |
| Jagannathprasad | 15 | Low | +7 | no | — | — | — | — |
| Bhanjanagar | 14 | Low | +6 | no | — | — | — | — |
