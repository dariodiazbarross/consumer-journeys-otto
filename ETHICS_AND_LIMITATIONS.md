# Ethics and limitations

This project predicts items associated with future observed cart/order actions.
It does **not** show that displaying a recommendation causes that action, improves
conversion, produces revenue, benefits the user, or measures preference or
intention. OTTO provides no randomized exposure log, counterfactual outcome,
price, margin, category, inventory, ranking-exposure or welfare measure. Offline
agreement is a prerequisite for a useful system, not evidence of online impact.

The anonymous identifiers reduce direct identifiability but do not make behavioral
data ethically neutral. Event histories can reveal routines and should be minimized,
protected, retention-limited and used for purposes people reasonably expect. This
repository publishes no event-level data or real session traces. Interpretability
examples are aggregate or synthetic. Do not combine the identifiers with other data
to profile or re-identify people.

Observable revisiting, exploration and action sequences are descriptions of logged
behavior. They are not psychological measurements of loyalty, indecision,
impulsivity, irrationality, preference strength or purchase intent. Cart activity
is operationally closer to purchase than a click, but remains an event label with
unknown commercial meaning and source logging error.

Popularity and transition signals reproduce the historical platform's exposure,
catalog and user base. They can concentrate attention on already-common products
and under-serve rare or newly introduced items. The error analysis separates head,
tail and rare targets, but cannot assess demographic fairness because demographics
are absent. Absence of a measured group disparity is not evidence of fairness.

The source consists of four training weeks and one test week, anonymized sessions,
items and actions. Session length may be capped at 500; users are disjoint between
source periods; the session is activity within a source period rather than a web
visit; the test catalog and historical environment are fixed. Results may not
generalize to another season, catalog, market, interface or objective. The protocol
conditions ranking evaluation on a future relevant action and therefore does not
estimate engagement propensity among all eligible sessions.

Timestamp ties are observational blocks. Exact duplicate events are retained because
there is no basis to decide which log row is erroneous, and their possible effect on
the five-event recommendation point is reported. The fixed five-event point,
24-hour target window, top-20 list, candidate rules, association cap, hand-set weights
and fixed historical snapshots are defensible design choices, not universal truths.
Bootstrap intervals quantify finite-prefix variation for this fitted offline system;
they do not reproduce retraining uncertainty or survey a superpopulation of weeks.

An online next step would preregister guardrail and primary metrics, randomize eligible
traffic between a simple baseline and the contextual system, log actual exposure and
availability, monitor concentration and latency, and measure user and commercial
outcomes over a sufficient horizon. That A/B test is proposed, not performed here.
