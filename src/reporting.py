"""Render the recruiter case study and technical report from verified JSON."""
# ruff: noqa: E501
import json

from src.common import ROOT


def read(name: str) -> dict:
    return json.loads((ROOT / "reports" / name).read_text())


def pct(value: float, decimals: int = 2) -> str:
    return f"{value*100:.{decimals}f}%"


def pp(record: dict) -> str:
    estimate = record["estimate"]*100
    lower, upper = (x*100 for x in record["ci95"])
    return f"{estimate:+.2f} pp (95% CI {lower:+.2f} to {upper:+.2f})"


def metric_table(results: dict) -> str:
    labels = {"global":"Global popularity", "recent":"Recent popularity", "repeat":"Recent repeat",
              "r":"+ Repetition", "ra":"+ Associations", "c":"+ Action/recency context"}
    lines = ["| Strategy | Recall@20 | MRR@20 |", "|---|---:|---:|"]
    for method, label in labels.items():
        recall, mrr = results["metrics"][f"{method}_recall"], results["metrics"][f"{method}_mrr"]
        lines.append(f"| {label} | {pct(recall['estimate'])} [{pct(recall['ci95'][0])}, {pct(recall['ci95'][1])}] | {pct(mrr['estimate'])} [{pct(mrr['ci95'][0])}, {pct(mrr['ci95'][1])}] |")
    return "\n".join(lines)


def write_reports() -> None:
    audit, test = read("data_audit.json"), read("results_test.json")
    flow = audit["sample_flow"]["test"]
    source = audit["source_ingestion"]["sources"]
    delta_repeat = test["differences"]["c_minus_repeat_recall"]
    delta_recent = test["differences"]["c_minus_recent_recall"]
    context_direction = "improved" if delta_repeat["estimate"] > 0 else "did not improve"
    executive = f"""# Executive summary

Recent behavioral context **{context_direction} Recall@20 relative to the strong recent-repeat baseline by {pp(delta_repeat)}** on {flow['target_positive']:,} final-test prefixes with an observed target. Relative to recent popularity, the difference was {pp(delta_recent)}. These are offline predictive differences, not causal or revenue effects.

The analysis processed all {source['train']['sessions']+source['test']['sessions']:,} source sessions and {source['train']['events']+source['test']['events']:,} events without sampling. A recommendation is made after five interactions (including the whole cutoff timestamp block); the target is the distinct item set at the first future cart/order timestamp within 24 hours. Historical features are fixed before each temporal period.

Candidate retrieval reached {pct(test['failure_decomposition']['candidate_recall'])} of target-item mass. The final contextual top 20 lost {pct(test['failure_decomposition']['ranking_lost_target_mass_c'])} after retrieval and {pct(test['failure_decomposition']['retrieval_lost_target_mass'])} before ranking, indicating where engineering effort should go. A controlled online experiment would still be required to estimate user or commercial impact.
"""
    (ROOT / "reports/EXECUTIVE_SUMMARY.md").write_text(executive, encoding="utf-8")

    data_quality = f"""# Data quality and sample flow

All source records were streamed and retained. Event Parquet totals {audit['source_ingestion']['sources']['train']['parquet_bytes']+audit['source_ingestion']['sources']['test']['parquet_bytes']:,} bytes (the original ZIP is recorded separately). Source-order timestamp inversions were **{source['train']['out_of_order_events']+source['test']['out_of_order_events']:,}**; duplicate session keys were **{audit['duplicate_session_keys']:,}**.

| Source | Sessions | Events | Exact duplicate event tuples | Adjacent equal timestamps | Starts non-click |
|---|---:|---:|---:|---:|---:|
| Train | {source['train']['sessions']:,} | {source['train']['events']:,} | {source['train']['duplicate_event_tuples']:,} | {source['train']['same_timestamp_adjacent']:,} | {source['train']['starts_nonclick']:,} |
| Test | {source['test']['sessions']:,} | {source['test']['events']:,} | {source['test']['duplicate_event_tuples']:,} | {source['test']['same_timestamp_adjacent']:,} | {source['test']['starts_nonclick']:,} |

Exact duplicates are not silently deleted: they are observed source interactions and can move a session to the fifth-event recommendation point. Timestamp ties are represented as blocks. The original position identifies the fifth row, while the entire block enters the prefix and no behavioral order is assigned inside it. Non-click starts are plausible under the source extraction and are retained.

## Final-test flow

| Step | Sessions |
|---|---:|
| Original test records | {flow['source_sessions']:,} |
| At least five interactions | {flow['sessions_at_least_five']:,} |
| Cutoff in test and complete 24-hour horizon | {flow['eligible_after_time_and_horizon']:,} |
| Positive next cart/order target (ranking denominator) | {flow['target_positive']:,} |
| Eligible but target-negative (journey denominator only) | {flow['target_negative']:,} |

The main exclusion after length eligibility is cohort-end censoring or a cutoff outside the defined period, not a requirement that a session remain active for 24 hours. Full data were used. Maximum observed worker RSS was {audit['resource_profile']['maximum_worker_rss_bytes']/2**20:.0f} MiB. Public-use logging does not expose the mechanism behind duplicate events, product availability, or exposure.
"""
    (ROOT / "DATA_QUALITY.md").write_text(data_quality, encoding="utf-8")

    technical = f"""# Technical report

## Protocol and results

Final test contains {flow['eligible_after_time_and_horizon']:,} eligible prefixes; {flow['target_positive']:,} have an observed first future cart/order target inside 24 hours. Primary and secondary metrics macro-average those positive prefixes. Brackets below are 95% paired session-bootstrap intervals (1,000 replicates, fixed seed).

{metric_table(test)}

Incremental Recall@20 differences:

- Repetition after recent popularity: {pp(test['differences']['r_minus_recent_recall'])}.
- Associations after repetition: {pp(test['differences']['ra_minus_r_recall'])}.
- Action/recency context after associations: {pp(test['differences']['c_minus_ra_recall'])}.
- Full context versus recent repeat: {pp(delta_repeat)}.

Validation used the preceding week with independently frozen history. Full validation metrics are machine-readable in `reports/results_validation.json`; it is a temporal replication and pipeline check, not a score-shopping stage.

## Retrieval and ranking

Candidate recall was {pct(test['failure_decomposition']['candidate_recall'])}. Target-item mass absent from candidates was {pct(test['failure_decomposition']['retrieval_lost_target_mass'])}; target mass retrieved but below the contextual top 20 was {pct(test['failure_decomposition']['ranking_lost_target_mass_c'])}. All-target candidate misses affected {pct(test['failure_decomposition']['all_targets_missed_by_candidates'])} of positive prefixes, compared with {pct(test['failure_decomposition']['all_targets_missed_by_c_top20'])} all-target top-20 misses.

## Interpretation

The ablation, subgroup and error tables answer whether context justified complexity under the frozen objective. Small or interval-compatible differences are reported as such. Recommendations predict logged action items; they do not show that exposure would cause those actions. Candidate improvements, catalog constraints, latency, concentration and online outcomes require production logs and a preregistered A/B test.

See `PROJECT_DESIGN.md`, `sql/`, the four executed notebooks and `ETHICS_AND_LIMITATIONS.md` for definitions, SQL grains, behavioral findings and limits.
"""
    (ROOT / "reports/TECHNICAL_REPORT.md").write_text(technical, encoding="utf-8")

    readme = f"""# Beyond Popularity: Consumer Journeys and Contextual Recommendations

**A SQL-first behavioral data science case study asking whether recent session context improves next cart/order recommendation over popularity and repeat baselines.**

![Incremental Recall@20](figures/04_incremental_recall.png)

## Executive finding

On {flow['target_positive']:,} held-out positive test prefixes, full context {context_direction} Recall@20 versus recent repeat by **{pp(delta_repeat)}** and differed from recent popularity by **{pp(delta_recent)}**. Candidate retrieval covered {pct(test['failure_decomposition']['candidate_recall'])} of target-item mass. The result quantifies offline agreement under a fixed protocol; it does not estimate recommendation-caused conversion or revenue.

{metric_table(test)}

## Why this question matters

Popularity is cheap, robust and often underestimated. Repeating recently viewed items is a strong behavioral baseline. More context is useful only if item transitions, action type and recency add material held-out value at an acceptable complexity cost. This project separates candidate retrieval from ranking so a missed target is diagnosed at the correct system layer.

## Data and consumer journeys

OTTO v1 contains {source['train']['events']+source['test']['events']:,} anonymous click, cart and order events across {source['train']['sessions']+source['test']['sessions']:,} official sessions over five weeks. Every event was processed; no row or session sampling. A session is one user's activity inside a source period, not a 30-minute visit. Prices, categories, demographics, inventory and recommendation exposure are unavailable and never invented.

![Journey depth](figures/02_journey_depth.png)

Journey analysis keeps simultaneous events as blocks, distinguishes repeats from breadth, and summarizes observable action-block transitions. It avoids psychological labels: a cart event is closer to purchase operationally, but is not a direct measure of intention.

## Frozen temporal design

One recommendation is made after the first five observed interactions, including every event tied at the cutoff timestamp. The target is the distinct item set at the first later cart/order timestamp within 24 hours. Weeks 1–3 build validation history; week 4 is validation; all four training weeks build final history; the official following week is untouched final test. History is strictly earlier than each period.

Candidates unite prefix items, 30 historical next-cart/order neighbors per prefix item, and 200 global plus 200 recent popular items. No target is injected. The fixed ablation adds session repetition, directional item associations, then transparent action/recency weights. There is no learned ranker, neural model or metric-driven retuning in V1.

```mermaid
flowchart LR
  A[Versioned JSONL ZIP] --> B[Whole-session Parquet partitions]
  B --> C[SQL events and timestamp blocks]
  C --> D[Historical popularity and associations]
  C --> E[Five-event prefixes and 24h targets]
  D --> F[Leakage-safe candidates]
  E --> F
  F --> G[Batched ranking]
  G --> H[Paired Recall@20 and MRR@20]
```

The seven auditable SQL files implement normalization, session and block aggregates, temporal history, prefix/target construction, associations, candidates and evaluation. High-risk joins have cardinality assertions; future-target mutation tests verify prefix invariance.

## What information adds value?

![Ablation differences](figures/05_ablation_differences.png)

The full contextual strategy's Recall@20 is {pct(test['metrics']['c_recall']['estimate'])}; its MRR@20 is {pct(test['metrics']['c_mrr']['estimate'])}. Associations added {pp(test['differences']['ra_minus_r_recall'])}; action/recency added {pp(test['differences']['c_minus_ra_recall'])}. The interpretation follows the observed size and uncertainty rather than declaring every nonzero change practically important.

## Where the system fails

![Retrieval and ranking failures](figures/06_failure_decomposition.png)

![Performance by item history](figures/07_popularity_errors.png)

The subgroup report includes head, tail, rare and mixed target sets; exactly-five versus cutoff-tie-extended prefixes; repeat-heavy versus broader exploration; and prior-cart/order versus click-only histories. Groups below 100 prefixes are not interpreted. Performance differences describe the logged test cohort and are not evidence of algorithm-caused discrimination.

## Business interpretation

- Use recent popularity as a dependable cold/fallback layer and recent repeat as the operational complexity benchmark.
- Add context only where the paired improvement, candidate coverage and latency justify it; the frozen ablation identifies the contributing signal.
- If retrieval loss dominates, improve candidate sources before tuning ranking. If ranking loss dominates, better candidate scoring is the more direct next step.
- Run a controlled online experiment with real exposure, inventory and guardrail logs before any claim about conversion, revenue, satisfaction or welfare.

## Limitations and ethics

This is historical, anonymous platform behavior without product or exposure context. The final test is one week; the ranking estimand conditions on an observed future action; duplicate events and source capping may affect journeys; fixed heuristic weights are not probabilities. Popularity can reinforce concentration and rare items are intrinsically difficult. See [Ethics and limitations](ETHICS_AND_LIMITATIONS.md).

## Reproduce

Python 3.13, DuckDB 1.5.5, PyArrow 23.0.1, pandas/NumPy and SQL. Raw and event-level files are ignored. A clean clone can run acquisition through reports using the commands in [data/README.md](data/README.md). CI uses synthetic data only and tests parsing, type mapping, ordering, tie-safe prefixes, horizon targets, temporal boundaries, leakage, candidates, metric math, deterministic ranks, join cardinality and reproducibility.

## Navigate

| Start here | Purpose |
|---|---|
| [Project design](PROJECT_DESIGN.md) | Frozen estimand, splits, candidates, metrics and limitations |
| [Data sources](DATA_SOURCES.md) / [license](DATA_LICENSE.md) | Version, hashes, attribution and transformation disclosure |
| [Data quality](DATA_QUALITY.md) | Full audit and transparent sample flow |
| [`sql/`](sql/) / [`src/`](src/) | Auditable analytical transformations and orchestration |
| [`notebooks/`](notebooks/) | Executed audit, journeys, baselines, evaluation and errors |
| [Technical report](reports/TECHNICAL_REPORT.md) | Complete metric and uncertainty interpretation |

**Boundary:** this is an interpretable OTTO V1 case study. A possible LightGBM ranker is documented only as future work; it is not implemented.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    write_reports()
