# Data quality and sample flow

All source records were streamed and retained. Event Parquet totals 1,822,065,710 bytes (the original ZIP is recorded separately). Source-order timestamp inversions were **0**; duplicate session keys were **0**.

| Source | Sessions | Events | Exact duplicate event tuples | Adjacent equal timestamps | Starts non-click |
|---|---:|---:|---:|---:|---:|
| Train | 12,899,779 | 216,716,096 | 331,159 | 2,668,780 | 55,572 |
| Test | 1,671,803 | 13,851,293 | 18,895 | 178,112 | 6,484 |

Exact duplicates are not silently deleted: they are observed source interactions and can move a session to the fifth-event recommendation point. Timestamp ties are represented as blocks. The original position identifies the fifth row, while the entire block enters the prefix and no behavioral order is assigned inside it. Non-click starts are plausible under the source extraction and are retained.

## Final-test flow

| Step | Sessions |
|---|---:|
| Original test records | 1,671,803 |
| At least five interactions | 769,655 |
| Cutoff in test and complete 24-hour horizon | 632,645 |
| Positive next cart/order target (ranking denominator) | 200,864 |
| Eligible but target-negative (journey denominator only) | 431,781 |

The main exclusion after length eligibility is cohort-end censoring or a cutoff outside the defined period, not a requirement that a session remain active for 24 hours. Full data were used. Maximum observed worker RSS was 586 MiB. Public-use logging does not expose the mechanism behind duplicate events, product availability, or exposure.
