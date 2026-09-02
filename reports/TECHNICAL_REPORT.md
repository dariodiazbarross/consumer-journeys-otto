# Technical report

## Protocol and results

Final test contains 632,645 eligible prefixes; 200,864 have an observed first future cart/order target inside 24 hours. Primary and secondary metrics macro-average those positive prefixes. Brackets below are 95% paired session-bootstrap intervals (1,000 replicates, fixed seed).

| Strategy | Recall@20 | MRR@20 |
|---|---:|---:|
| Global popularity | 0.53% [0.50%, 0.56%] | 0.15% [0.14%, 0.16%] |
| Recent popularity | 0.77% [0.73%, 0.81%] | 0.38% [0.35%, 0.40%] |
| Recent-item baseline | 47.90% [47.68%, 48.11%] | 40.56% [40.36%, 40.76%] |
| + Repeat-frequency score | 47.90% [47.68%, 48.11%] | 32.69% [32.52%, 32.86%] |
| + Associations | 54.46% [54.24%, 54.66%] | 33.60% [33.42%, 33.76%] |
| + Action/recency context | 54.38% [54.16%, 54.58%] | 35.63% [35.45%, 35.80%] |

Incremental Recall@20 differences:

- Repeat-frequency score after recent popularity: +47.13 pp (95% CI +46.92 to +47.33).
- Associations after the repeat-frequency score: +6.56 pp (95% CI +6.45 to +6.67).
- Action/recency context after associations: -0.08 pp (95% CI -0.11 to -0.06).
- Full context versus the recent-item baseline: +6.48 pp (95% CI +6.37 to +6.59).

Validation used the preceding week with independently frozen history. Full validation metrics are machine-readable in `reports/results_validation.json`; it is a temporal replication and pipeline check, not a score-shopping stage.

## Retrieval and ranking

Candidate recall was 56.12%. Target-item mass absent from candidates was 43.88%; target mass retrieved but below the contextual top 20 was 1.75%. All-target candidate misses affected 43.65% of positive prefixes, compared with 45.40% all-target top-20 misses.

## Interpretation

The ablation, subgroup and error tables answer whether context justified complexity under the frozen objective. Small or interval-compatible differences are reported as such. Recommendations predict logged action items; they do not show that exposure would cause those actions. Candidate improvements, catalog constraints, latency, concentration and online outcomes require production logs and a preregistered A/B test.

See `PROJECT_DESIGN.md`, `sql/`, the four executed notebooks and `ETHICS_AND_LIMITATIONS.md` for definitions, SQL grains, behavioral findings and limits.
