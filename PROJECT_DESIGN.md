# Frozen design — OTTO V1

Frozen on 2026-08-31, before constructing historical recommendation signals or
examining recommendation results. The source audit is permitted before this
freeze. The initial Git commit preserves this document. No metric-driven changes.

## Question and estimand

How much does recent behavioral context improve recommendation of products
receiving the next cart or order action compared with popularity and a recent-item
baseline? The estimand is the **mean per-prefix Recall@20**, conditional on an
observable next cart/order within 24 hours, for eligible official test sessions.
This is offline prediction, not a treatment effect or revenue estimate.

## Measurement and population

- A session is OTTO's activity of one anonymized user inside a source period,
  not a 30-minute visit. Retain source sessions; no re-sessionization.
- One event is `(session, original event_index)` with item `aid`, Unix millisecond
  timestamp `ts`, and action `clicks=0`, `carts=1`, `orders=2`.
- One recommendation is made immediately after the fifth observed interaction.
  Sort by timestamp, using original position only to identify row five. Include
  **all** events with the same timestamp as row five. Their within-block order
  has no behavioral interpretation. No item-ID ordering of behavior.
- One prefix contains events with `ts <= cutoff`. Full-session statistics are
  descriptive only. Candidate ranking grain is `(session, aid)`.
- A target is the distinct set of items at the **first** timestamp strictly
  after cutoff containing carts/orders, if at most 24 hours later.
- Eligibility: at least five interactions; cutoff inside the evaluation period;
  cutoff + 24 hours no later than the period end. Inactivity is valid: a session
  does not need to continue for 24 hours. Period-end censoring is distinct.
- Keep target-negative eligible sessions in descriptive denominators. Primary
  ranking metrics condition on a positive target; they do not measure whether
  a future action occurs. Publish the entire sample flow.

## Time boundaries

Derive exact boundaries from audited source timestamps, without inspecting model
scores: official test start is its minimum timestamp rounded down to an hour;
test end is its maximum timestamp rounded up to an hour. Check coverage is seven
days and training ends before test start. Validation is the preceding seven days.
Weeks 1–3 construct validation history. All training events strictly before the
official test start construct final test history. Record resolved UTC boundaries
in `reports/boundaries.json` before running recommendation methods.

Only historical events strictly before the relevant split start enter popularity
and association tables. Statistics are fixed for each evaluation period; there
is no online refresh. Validation uses late-starting training prefixes, so earlier
events from the same official training session may be in historical statistics.
This is observable past, not future leakage; no user-ID feature is used. Official
training and test users are disjoint. Test outcomes are used only for final
evaluation. No random train/test split.

## Historical signals and candidate retrieval

1. Global popularity: number of distinct historical sessions interacting with
   each item (any action). Recent popularity: the same count in the last seven
   days before the historical cutoff. Ties resolve by numeric item ID.
2. Associations: directional transitions between **consecutive distinct timestamp
   blocks** in a historical session, at most 24 hours apart. The destination
   block must contain cart/order actions; only those destination items count.
   Both blocks must contain at most ten distinct items, preventing large
   simultaneous baskets from generating quadratic artifacts. All cross-block
   pairs count; exclude same-item pairs. Count a session at most once per pair.
   Report omitted large-block transitions. Keep the top 30 destinations per
   source item, requiring support from at least two sessions. Association
   strength is pair support divided by the sum of retained outgoing supports.
3. Candidate union: every distinct prefix item, top-30 historical neighbors for
   every prefix item, top-200 global items, top-200 recent items. Deduplicate
   `(session, aid)`. No target table is used in retrieval or scoring. No target
   injection. Missing historical signals become zero. No unavailable inventory
   filter. Rank ties use aid solely as a deterministic ranking rule.

## Prespecified methods and ablations

All constants below are fixed; no tuning grid or learned ranker in V1.
Validation checks the pipeline and provides an earlier-period replication; it
does not select the most favorable method. Always report all methods.

Let `p = 1 / (1 + recent_popularity_rank)` for recent top-200 items, otherwise 0.
Let `r_i` be prefix interaction count divided by the largest count among prefix
items. Let `a_i` be the mean outgoing association strength from distinct prefix
items (unmatched sources contribute zero).

| Method | Ranking rule |
|---|---|
| Global popularity | Historical popularity descending |
| Recent popularity (P) | Seven-day historical popularity descending |
| Recent-item baseline | Seen items first, latest observed timestamp descending, count descending; recent then global popularity fallback |
| + Repeat-frequency score (R) | `r_i + 0.05 p_i` |
| + Associations (RA) | `r_i + a_i + 0.05 p_i` |
| + Action/recency context (C) | `r*_i + a*_i + 0.05 p_i` |

For C, each prefix event has weight `action_weight * 2 ** (-age_hours / 6)`;
click/cart/order weights are 1/3/2. `r*` sums these weights by item and divides by
the largest item weight. `a*` averages association strengths using these item
weights, divided by total prefix weight. These weights are transparent heuristics,
not measurements of intention or optimized business values. The methods are
scores, not calibrated probabilities. All methods return at most 20 unique items.
The popularity baselines use their own top-20 lists; R/RA/C share the candidate
union so changes after R isolate ranking information. The recent-item baseline is a strong
additional comparator, not hidden inside the ablation.

## Metrics and uncertainty

- Primary: macro Recall@20 = mean(number of distinct targets in top 20 / target
  set size). Multiple simultaneous targets each have equal weight within prefix.
- Secondary: MRR@20 = mean reciprocal rank of the first relevant item, zero if
  absent. For singleton targets HitRate@20 equals Recall@20, not separate evidence.
- Candidate recall is the same recall formula over the entire candidate set.
  Lost target mass is decomposed exactly into `1 - candidate_recall` (retrieval)
  and `candidate_recall - recall@20` (ranking). Also report all-target-missed
  prefix rates and unique recommendation/catalog coverage.
- Paired bootstrap: 1,000 resamples of sessions/prefixes with replacement,
  seed 20260831, percentile 95% intervals. Same resampled indices for all methods.
  One prefix per session avoids event-level pseudo-replication. Intervals are
  conditional on fitted historical tables and this observed week, not uncertainty
  over retraining, future weeks, or causal effects. No multiplicity-adjusted claims.
- Compare every incremental step, C versus the recent-item baseline, and C versus popularity.
  Report percentage-point differences and interval widths, including null results.

## Error and journey analyses

Before recommendation evaluation summarize source depth, duration, revisits,
action composition, and consecutive timestamp-block action transitions. Mixed
action blocks are separate, never silently ordered. Distinguish observation,
prediction, and causality throughout.

Prespecified groups: target items seen in fewer than five historical sessions
(rare); top 1% of historical item ranks (head); other items (tail), with mixed-set
prefixes separate. Prefixes of exactly five versus more than five events; repeat
share at least 40% versus lower; previous cart versus none; click-only versus
other action history. Report N, Recall/MRR, candidate coverage and uncertainty;
do not interpret groups with fewer than 100 prefixes. Bootstrap subgroup
performance and C-to-recent-item-baseline differences. These are behavioral descriptions,
not psychological segments.

## Audit, exclusions and scale

Reject missing/invalid keys, noninteger/negative identifiers, unknown action
types, invalid timestamp units, or duplicate session IDs. Preserve exact duplicate
event tuples as observed interactions, quantify them, and discuss their effect
on reaching five interactions. Chronological normalization must not invent
within-timestamp order. Do not remove starts with carts/orders or long sessions
merely because they look unusual.

Attempt all source records, all historical signals and the full defined evaluation
cohorts with bounded Parquet partitions, DuckDB memory limits and batched ranking.
No sampling is planned. If a measured resource limit forces whole-session
sampling, document the genuine issue, seed, fraction and distribution changes
before running recommendations. Never sample isolated events.

## Limitations and changes

Historical platform data, source selection/capping, missing exposure/inventory/
price/category information, positive-target conditioning, fixed five-event
timing, 24-hour horizon, and only one final week limit generalization. Anonymity
does not justify profiling individuals. No causal, revenue, conversion, ROI,
psychological or welfare claims. No V2 or other project implementation.

Change log: no changes at freeze. Any subsequent amendment must state what, why,
when, and its interpretation impact; implementation corrections that restore
this contract are recorded separately in the quality audit.
