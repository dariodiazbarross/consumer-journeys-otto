# Executive summary

Recent behavioral context **improved Recall@20 relative to the strong recent-repeat baseline by +6.48 pp (95% CI +6.37 to +6.59)** on 200,864 final-test prefixes with an observed target. Relative to recent popularity, the difference was +53.60 pp (95% CI +53.38 to +53.80). These are offline predictive differences, not causal or revenue effects.

The analysis processed all 14,571,582 source sessions and 230,567,389 events without sampling. A recommendation is made after five interactions (including the whole cutoff timestamp block); the target is the distinct item set at the first future cart/order timestamp within 24 hours. Historical features are fixed before each temporal period.

Candidate retrieval reached 56.12% of target-item mass. The final contextual top 20 lost 1.75% after retrieval and 43.88% before ranking, indicating where engineering effort should go. A controlled online experiment would still be required to estimate user or commercial impact.
