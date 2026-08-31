"""Generate and execute four concise analytical notebooks from final evidence."""
# ruff: noqa: E501, E702
import os
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

from src.common import ROOT


def code(text: str):
    return nbf.v4.new_code_cell(text)


def markdown(text: str):
    return nbf.v4.new_markdown_cell(text)


def build(title: str, purpose: str, cells: list, ending: str) -> nbf.NotebookNode:
    notebook = nbf.v4.new_notebook()
    notebook.metadata.kernelspec = {"display_name":"Python 3", "language":"python", "name":"python3"}
    notebook.metadata.language_info = {"name":"python", "version":"3.13"}
    notebook.cells = [markdown(f"# {title}\n\n{purpose}\n\n**Executed artifact:** reusable transformations live in `src/` and `sql/`; this notebook reads compact, versioned evidence rather than reprocessing 230 million events interactively.")]
    notebook.cells += cells
    notebook.cells += [markdown(ending)]
    return notebook


def create_notebooks() -> None:
    output = ROOT / "notebooks"; output.mkdir(exist_ok=True)
    setup = """import json
from pathlib import Path
import pandas as pd
ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
def report(name): return json.loads((ROOT/'reports'/name).read_text())"""
    notebooks = {
        "01_data_audit.ipynb": build("01 — Data audit", "Validate source scale, timestamps, duplicates, ties and the sample flow before interpretation.", [
            code(setup),
            markdown("## Source integrity\n\nExact duplicates and simultaneous events are reported, retained and handled explicitly. Source positions are never presented as behavioral ordering inside a timestamp tie."),
            code("a=report('data_audit.json')\npd.DataFrame(a['session_summary'])"),
            code("pd.DataFrame(a['sample_flow']).T"),
            code("{k: {x: a['source_ingestion']['sources'][k][x] for x in ['minimum_utc','maximum_utc','duplicate_event_tuples','same_timestamp_adjacent','out_of_order_events']} for k in ['train','test']}")
        ], "## KEY FINDINGS\n\nAll official records were processed; exact duplicates and timestamp ties are nonzero and therefore material analytical contracts. The final ranking denominator is explicitly target-positive and smaller than the eligible journey cohort.\n\n## LIMITATIONS\n\nThe source cannot reveal which exact duplicates are logging error or real repeated requests. Session boundaries come from OTTO.\n\n## NEXT STEP\n\nDescribe observable journeys using timestamp blocks, keeping predictive features separate."),
        "02_consumer_journeys.ipynb": build("02 — Consumer journeys", "Describe depth, duration, repeat breadth and action-block transitions before recommendation evaluation.", [
            code(setup),
            code("a=report('data_audit.json')\npd.DataFrame(a['session_summary'])[['source','median_events','mean_events','median_duration_hours','mean_repeat_share']]"),
            code("t=pd.DataFrame(a['action_block_transitions']); t.assign(transition_share=t.transitions/t.groupby(['source','source_action']).transitions.transform('sum')).query(\"source=='test'\").head(16)"),
            markdown("![Journey depth](../figures/02_journey_depth.png)\n\n![Block transitions](../figures/03_action_transitions.png)")
        ], "## KEY FINDINGS\n\nJourney depth is strongly right-skewed; timestamp-block transitions are dominated by observable clicks, with carts, orders and mixed blocks kept distinct. Repeat share describes logged breadth, not loyalty or indecision.\n\n## LIMITATIONS\n\nActions lack price, category, availability and exposure context; blocks do not reveal within-timestamp order.\n\n## NEXT STEP\n\nCompare frozen popularity and recent-repeat baselines before adding context."),
        "03_recommendation_baselines.ipynb": build("03 — Recommendation baselines", "Examine temporal validation and the incremental, fixed-score strategy design.", [
            code(setup),
            code("p=json.loads((ROOT/'config/protocol.json').read_text()); p"),
            code("v=report('results_validation.json')\npd.DataFrame([{'strategy':k.replace('_recall',''),'recall@20':x['estimate'],'lower':x['ci95'][0],'upper':x['ci95'][1]} for k,x in v['metrics'].items() if k.endswith('_recall')])"),
            markdown("The validation week checks temporal replication and pipeline behavior. It does not select a favorable target, candidate rule or metric.")
        ], "## KEY FINDINGS\n\nPopularity and recent repeat provide nontrivial benchmarks. Incremental strategies share the same candidate pool after repetition so the ablation isolates information used in ranking.\n\n## LIMITATIONS\n\nHand-set scores are transparent heuristics, not calibrated probabilities; validation is one week.\n\n## NEXT STEP\n\nEvaluate the untouched test week with paired uncertainty and diagnose retrieval versus ranking."),
        "04_evaluation_and_errors.ipynb": build("04 — Evaluation and errors", "Answer the primary question on the untouched final period and translate failures responsibly.", [
            code(setup),
            code("r=report('results_test.json')\npd.DataFrame([{'strategy':k.replace('_recall',''),'recall@20':x['estimate'],'ci95':x['ci95']} for k,x in r['metrics'].items() if k.endswith('_recall')])"),
            code("pd.DataFrame(r['differences']).T"),
            code("pd.Series(r['failure_decomposition'])"),
            code("pd.DataFrame(r['subgroups']['target_popularity_group'])"),
            markdown("![Final comparison](../figures/04_incremental_recall.png)\n\n![Failure decomposition](../figures/06_failure_decomposition.png)")
        ], "## KEY FINDINGS\n\nThe primary estimate, paired interval and ablation quantify whether recent behavioral context adds practical held-out information. Retrieval and ranking losses are reported separately; rare/head/tail behavior identifies specific limits.\n\n## LIMITATIONS\n\nOffline prediction does not identify recommendation-caused behavior, user welfare, conversion, revenue or ROI. Intervals condition on the fitted histories and one test week.\n\n## NEXT STEP\n\nIf complexity is justified, specify latency and concentration constraints and run a preregistered online A/B test with real exposure and inventory logs."),
    }
    old = Path.cwd(); os.chdir(ROOT)
    try:
        for name, notebook in notebooks.items():
            client = NotebookClient(notebook, timeout=120, kernel_name="python3", resources={"metadata":{"path":str(ROOT)}})
            client.execute()
            nbf.write(notebook, output/name)
            print(f"executed {name}")
    finally:
        os.chdir(old)


if __name__ == "__main__":
    create_notebooks()
