-- Inputs: batch_items (only observed prefix information), popularity, neighbors.
-- NO target/outcome table is referenced anywhere in retrieval or scoring.
CREATE OR REPLACE TEMP TABLE observed_signals AS
SELECT *, interactions::DOUBLE / max(interactions) OVER (PARTITION BY session) AS repetition,
       context_weight / max(context_weight) OVER (PARTITION BY session) AS context_repetition,
       context_weight / sum(context_weight) OVER (PARTITION BY session) AS source_weight,
       count(*) OVER (PARTITION BY session) AS source_count
FROM batch_items;

CREATE OR REPLACE TEMP TABLE association_signals AS
SELECT o.session, n.aid,
       sum(n.strength / o.source_count) AS association,
       sum(n.strength * o.source_weight) AS context_association
FROM observed_signals o JOIN neighbors n ON o.aid = n.source_aid
GROUP BY o.session, n.aid;

CREATE OR REPLACE TEMP TABLE candidates AS
WITH candidate_union AS (
    SELECT session, aid FROM observed_signals
    UNION
    SELECT session, aid FROM association_signals
    UNION
    SELECT s.session, p.aid FROM (SELECT DISTINCT session FROM batch_items) s
    CROSS JOIN (SELECT aid FROM popularity WHERE global_rank <= 200 OR recent_rank <= 200) p
)
SELECT c.session, c.aid,
       o.aid IS NOT NULL AS seen, a.aid IS NOT NULL AS neighbor,
       coalesce(o.last_seen, -1) AS last_seen,
       coalesce(o.interactions, 0) AS interactions,
       coalesce(p.global_rank, 2147483647) AS global_rank,
       coalesce(p.recent_rank, 2147483647) AS recent_rank,
       CASE WHEN p.recent_rank <= 200 THEN 1.0/(1+p.recent_rank) ELSE 0 END AS popular,
       coalesce(o.repetition, 0) AS repetition,
       coalesce(o.context_repetition, 0) AS context_repetition,
       coalesce(a.association, 0) AS association,
       coalesce(a.context_association, 0) AS context_association
FROM candidate_union c
LEFT JOIN observed_signals o ON c.session=o.session AND c.aid=o.aid
LEFT JOIN association_signals a ON c.session=a.session AND c.aid=a.aid
LEFT JOIN popularity p ON c.aid=p.aid;

CREATE OR REPLACE TEMP TABLE ranks AS
SELECT session, aid,
       row_number() OVER (PARTITION BY session ORDER BY global_rank, aid) AS global_rank,
       row_number() OVER (PARTITION BY session ORDER BY recent_rank, global_rank, aid) AS recent_rank,
       row_number() OVER (PARTITION BY session ORDER BY seen DESC, last_seen DESC,
                          interactions DESC, recent_rank, global_rank, aid) AS repeat_rank,
       row_number() OVER (PARTITION BY session ORDER BY repetition + 0.05*popular DESC, aid) AS r_rank,
       row_number() OVER (PARTITION BY session ORDER BY repetition + association + 0.05*popular DESC, aid) AS ra_rank,
       row_number() OVER (PARTITION BY session ORDER BY context_repetition + context_association + 0.05*popular DESC, aid) AS c_rank
FROM candidates;
