-- Recommendation/target boundary: prefix <= cutoff; future > cutoff.
CREATE OR REPLACE TEMP TABLE eligible AS
SELECT session, cutoff FROM sessions
WHERE n_events >= 5 AND cutoff >= getvariable('period_start')
  AND cutoff + 86400000 <= getvariable('period_end');

CREATE OR REPLACE TEMP TABLE prefix_events AS
SELECT e.session, e.aid, e.ts, e.action, e.ordinal, p.cutoff
FROM events e INNER JOIN eligible p ON e.session = p.session
WHERE e.ts <= p.cutoff;

CREATE OR REPLACE TEMP TABLE prefix_items AS
SELECT session, aid, cutoff, count(*) AS interactions,
       min(ts) AS first_seen, max(ts) AS last_seen,
       count(*) FILTER (WHERE action = 1) AS cart_count,
       count(*) FILTER (WHERE action = 2) AS order_count,
       sum(CASE action WHEN 0 THEN 1 WHEN 1 THEN 3 ELSE 2 END
           * power(2.0, -(cutoff-ts) / 21600000.0)) AS context_weight
FROM prefix_events GROUP BY session, aid, cutoff;

CREATE OR REPLACE TEMP TABLE prefixes AS
WITH observed AS (
    SELECT session, cutoff, sum(interactions) AS prefix_length,
           count(*) AS distinct_items, sum(cart_count) AS prefix_carts,
           sum(order_count) AS prefix_orders,
           1.0-count(*)::DOUBLE/sum(interactions) AS repeat_share
    FROM prefix_items GROUP BY session, cutoff
), first_future AS (
    SELECT e.session, min(e.ts) AS target_ts
    FROM events e JOIN eligible p ON e.session = p.session
    WHERE e.ts > p.cutoff AND e.ts <= p.cutoff + 86400000
      AND e.ts < getvariable('period_end') AND e.action > 0
    GROUP BY e.session
), target_sets AS (
    SELECT f.session, f.target_ts, list_sort(list(DISTINCT e.aid)) AS targets
    FROM first_future f JOIN events e
      ON e.session = f.session AND e.ts = f.target_ts AND e.action > 0
    GROUP BY f.session, f.target_ts
)
SELECT o.*, t.target_ts, t.targets,
       coalesce(len(t.targets), 0) AS target_count
FROM observed o LEFT JOIN target_sets t ON o.session = t.session;
