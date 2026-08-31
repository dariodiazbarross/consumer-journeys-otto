-- Full-session attributes are DESCRIPTIVE ONLY; never passed to scoring.
-- Grain/key: session. Fifth timestamp is tie-invariant.
CREATE OR REPLACE TEMP TABLE sessions AS
SELECT session, count(*) AS n_events, count(DISTINCT aid) AS n_items,
       min(ts) AS first_ts, max(ts) AS last_ts,
       max(ts) FILTER (WHERE ordinal = 5) AS cutoff,
       count(*) FILTER (WHERE action = 0) AS clicks,
       count(*) FILTER (WHERE action = 1) AS carts,
       count(*) FILTER (WHERE action = 2) AS orders,
       1.0 - count(DISTINCT aid)::DOUBLE / count(*) AS repeat_share,
       (max(ts)-min(ts)) / 3600000.0 AS duration_hours
FROM events GROUP BY session;

CREATE OR REPLACE TEMP TABLE action_transitions AS
SELECT block_action AS source_action, next_action AS destination_action,
       count(*) AS transitions
FROM block_sequence WHERE next_ts IS NOT NULL
GROUP BY block_action, next_action;
