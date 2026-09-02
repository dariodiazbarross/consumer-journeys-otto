"""Create the seven case-study figures from compact, verified reports."""
# ruff: noqa: E501, E701, E702, E741, I001
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.common import ROOT

BLUE, TEAL, ORANGE, GREY, NAVY = "#2F5D7E", "#2A9D8F", "#E9A23B", "#8C98A4", "#17324D"
LABELS = {0: "Click", 1: "Cart", 2: "Order", 3: "Mixed"}


def load(name: str) -> dict:
    return json.loads((ROOT / "reports" / name).read_text())


def finish(name: str, source: str = "Source: OTTO Recommender Systems Dataset v1; author's analysis.") -> None:
    plt.figtext(.01, .01, source, fontsize=8, color="#5E6973")
    plt.tight_layout(rect=(0, .055, 1, 1))
    plt.savefig(ROOT / "figures" / f"{name}.png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close()


def create_figures() -> None:
    (ROOT / "figures").mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    audit = load("data_audit.json")
    rows = pd.DataFrame(audit["session_summary"]).set_index("source").loc[["train", "test"]]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    rows[["clicks", "carts", "orders"]].div(rows.events, axis=0).mul(100).plot(
        kind="bar", stacked=True, color=[BLUE, ORANGE, TEAL], ax=axes[0], rot=0)
    axes[0].set(title="Actions are dominated by product views\nShare of all events by source period", ylabel="Events (%)", xlabel="")
    axes[0].legend(["Click", "Cart", "Order"], frameon=False)
    axes[1].bar(["Train", "Test"], rows.sessions/1e6, color=[NAVY, TEAL])
    axes[1].set(title="14.6 million official sessions\nAll source records processed", ylabel="Sessions (millions)")
    finish("01_source_scale")

    ingestion = audit["source_ingestion"]["sources"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for source, color in (("train", BLUE), ("test", TEAL)):
        hist = ingestion[source]["length_histogram"]
        x = np.array([int(k) for k in hist if int(k)<=50]); y = np.array([hist[str(k)] for k in x])
        ax.plot(x, np.cumsum(y)/sum(hist.values())*100, label=source.title(), color=color, linewidth=2.5)
    ax.set(title="Most journeys are short, while a small tail is deep\nCumulative share of sessions by observed event count", xlabel="Events in official session", ylabel="Sessions at or below threshold (%)", xlim=(2,50), ylim=(0,100))
    ax.legend(frameon=False)
    finish("02_journey_depth")

    trans = pd.DataFrame(audit["action_block_transitions"])
    pivot = trans.query("source=='test'").pivot(index="source_action", columns="destination_action", values="transitions").fillna(0)
    pivot = pivot.div(pivot.sum(axis=1), axis=0).mul(100).reindex(index=range(4), columns=range(4), fill_value=0)
    fig, ax = plt.subplots(figsize=(7,5.2)); sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues", cbar_kws={"label":"Within-source transition (%)"}, ax=ax)
    ax.set(title="Observable action blocks usually remain clicks\nConsecutive timestamp blocks; mixed blocks are kept explicit", xlabel="Next block", ylabel="Current block", xticklabels=[LABELS[i] for i in range(4)], yticklabels=[LABELS[i] for i in range(4)])
    finish("03_action_transitions")

    test = load("results_test.json")
    methods = ["global","recent","repeat","r","ra","c"]
    labels = ["Global pop.","Recent pop.","Recent-item\nbaseline","+ Repeat-frequency\nscore","+ Associations","+ Action/recency"]
    estimates = [test["metrics"][f"{m}_recall"]["estimate"]*100 for m in methods]
    intervals = [test["metrics"][f"{m}_recall"]["ci95"] for m in methods]
    errors = np.array([[e-l*100, u*100-e] for e,(l,u) in zip(estimates,intervals)]).T
    fig, ax=plt.subplots(figsize=(10,5.2)); colors=[GREY,GREY,ORANGE,BLUE,BLUE,TEAL]
    ax.bar(labels, estimates, color=colors, yerr=errors, capsize=3)
    ax.set(title="Context is evaluated against strong, simple baselines\nFinal test; macro Recall@20 with paired-session bootstrap intervals", ylabel="Recall@20 (%)", xlabel=""); ax.tick_params(axis="x", rotation=18)
    finish("04_incremental_recall")

    names=["r_minus_recent_recall","ra_minus_r_recall","c_minus_ra_recall","c_minus_repeat_recall"]
    labels2=["Repeat-frequency vs recent pop.","Associations after repeat-frequency","Action/recency after associations","Full context vs recent-item baseline"]
    d=[test["differences"][n]["estimate"]*100 for n in names]; ci=[test["differences"][n]["ci95"] for n in names]
    xerr=np.array([[v-l*100,u*100-v] for v,(l,u) in zip(d,ci)]).T
    fig,ax=plt.subplots(figsize=(9,5)); ax.errorbar(d,labels2,xerr=xerr,fmt="o",color=TEAL,capsize=4,markersize=8); ax.axvline(0,color="#333",linewidth=1)
    ax.set(title="Ablations show which information adds value\nPercentage-point Recall@20 differences; 95% paired bootstrap intervals", xlabel="Recall@20 difference (percentage points)", ylabel="")
    finish("05_ablation_differences")

    f=test["failure_decomposition"]; vals=[test["metrics"]["c_recall"]["estimate"],f["ranking_lost_target_mass_c"],f["retrieval_lost_target_mass"]]
    fig,ax=plt.subplots(figsize=(8,4.7)); ax.barh(["Reached by contextual top 20","Retrieved but ranked below 20","Absent from candidates"],np.array(vals)*100,color=[TEAL,ORANGE,GREY])
    ax.set(title="Candidate retrieval and ranking are separate failure modes\nDecomposition of target-item mass in final test", xlabel="Target-item mass (%)", ylabel="", xlim=(0,100))
    for i,v in enumerate(vals): ax.text(v*100+.8,i,f"{v*100:.1f}%",va="center")
    finish("06_failure_decomposition")

    groups=pd.DataFrame(test["subgroups"]["target_popularity_group"]); order=[x for x in ["head","tail","rare","mixed"] if x in set(groups.group)]; groups=groups.set_index("group").loc[order]
    fig,ax=plt.subplots(figsize=(8.5,5)); x=np.arange(len(groups)); w=.36
    ax.bar(x-w/2,groups.repeat_recall*100,w,label="Recent-item baseline",color=ORANGE); ax.bar(x+w/2,groups.c_recall*100,w,label="Full context",color=TEAL)
    ax.set(title="Item history defines where recommendation is hardest\nRecall@20 by target popularity group; labels show evaluated prefixes", ylabel="Recall@20 (%)",xlabel="",xticks=x,xticklabels=[f"{v.title()}\nN={groups.loc[v,'n']:,}" for v in groups.index]); ax.legend(frameon=False)
    finish("07_popularity_errors")


if __name__ == "__main__":
    create_figures()


