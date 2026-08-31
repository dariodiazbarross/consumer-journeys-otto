-- Input: raw_events. Grain: one source record position within session.
-- Timestamp normalization never gives item ID a behavioral ordering role.
CREATE OR REPLACE TEMP TABLE events AS
SELECT session, aid, ts, action, event_index,
       row_number() OVER (PARTITION BY session ORDER BY ts, event_index) AS ordinal,
       lag(ts) OVER (PARTITION BY session ORDER BY event_index) AS previous_source_ts
FROM raw_events;

-- One row per timestamp block. Mixed action blocks remain mixed.
CREATE OR REPLACE TEMP TABLE blocks AS
SELECT session, ts, count(*) AS n_events,
       list(DISTINCT aid) AS items,
       list(DISTINCT aid) FILTER (WHERE action > 0) AS relevant_items,
       count(DISTINCT aid) AS n_items,
       CASE WHEN count(DISTINCT action) > 1 THEN 3 ELSE min(action) END AS block_action
FROM events GROUP BY session, ts;

CREATE OR REPLACE TEMP TABLE block_sequence AS
SELECT *,
       lead(ts) OVER journey AS next_ts,
       lead(block_action) OVER journey AS next_action,
       sum(n_events) OVER (PARTITION BY session ORDER BY ts
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_events
FROM blocks
WINDOW journey AS (PARTITION BY session ORDER BY ts);
