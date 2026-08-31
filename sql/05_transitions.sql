-- Rebuild blocks after the temporal filter. No future block can leak backwards.
CREATE OR REPLACE TEMP TABLE historical_blocks AS
SELECT session, ts, list(DISTINCT aid) AS items,
       list(DISTINCT aid) FILTER (WHERE action > 0) AS relevant_items,
       count(DISTINCT aid) AS n_items
FROM historical_events GROUP BY session, ts;

CREATE OR REPLACE TEMP TABLE block_pairs AS
WITH next_block AS (
    SELECT *, lead(ts) OVER (PARTITION BY session ORDER BY ts) AS next_ts
    FROM historical_blocks
)
SELECT a.session, a.ts, a.items, a.n_items,
       b.ts AS next_ts, b.relevant_items, b.n_items AS next_n_items
FROM next_block a JOIN historical_blocks b
  ON a.session = b.session AND a.next_ts = b.ts
WHERE b.ts - a.ts <= 86400000 AND len(b.relevant_items) > 0;

CREATE OR REPLACE TEMP TABLE pair_counts AS
WITH expanded AS (
    SELECT session, unnest(items) AS source_aid, relevant_items
    FROM block_pairs WHERE n_items <= 10 AND next_n_items <= 10
), destinations AS (
    SELECT session, source_aid, unnest(relevant_items) AS aid FROM expanded
)
SELECT source_aid, aid, count(DISTINCT session) AS support
FROM destinations WHERE source_aid <> aid GROUP BY source_aid, aid;
