-- getvariable('history_end') is strictly earlier than evaluation outcomes.
-- Whole sessions stay inside source partitions, so partial support counts add.
CREATE OR REPLACE TEMP TABLE historical_events AS
SELECT * FROM events WHERE ts < getvariable('history_end');

CREATE OR REPLACE TEMP TABLE item_counts AS
WITH session_item AS (
    SELECT session, aid, max(ts) AS last_seen,
           count(*) FILTER (WHERE action > 0) AS relevant_actions
    FROM historical_events GROUP BY session, aid
)
SELECT aid, count(*) AS support,
       count(*) FILTER (WHERE last_seen >= getvariable('history_end') - 604800000) AS recent_support,
       sum(relevant_actions) AS cart_order_events
FROM session_item GROUP BY aid;
