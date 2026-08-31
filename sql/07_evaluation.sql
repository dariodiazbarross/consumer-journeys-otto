-- Targets first enter the pipeline HERE, after immutable candidate rankings.
-- One row per prefix; distinct target sets prevent duplicate action double-counts.
CREATE OR REPLACE TEMP TABLE evaluated AS
WITH target_items AS (
    SELECT session, target_count, unnest(targets) AS aid FROM batch_prefixes
), matched AS (
    SELECT t.*, r.global_rank, r.recent_rank, r.repeat_rank, r.r_rank, r.ra_rank, r.c_rank,
           r.aid IS NOT NULL AS retrieved
    FROM target_items t LEFT JOIN ranks r ON t.session=r.session AND t.aid=r.aid
)
SELECT session, max(target_count) AS target_count,
       avg(retrieved::DOUBLE) AS candidate_recall,
       avg(coalesce(global_rank <= 20, false)::DOUBLE) AS global_recall,
       avg(coalesce(recent_rank <= 20, false)::DOUBLE) AS recent_recall,
       avg(coalesce(repeat_rank <= 20, false)::DOUBLE) AS repeat_recall,
       avg(coalesce(r_rank <= 20, false)::DOUBLE) AS r_recall,
       avg(coalesce(ra_rank <= 20, false)::DOUBLE) AS ra_recall,
       avg(coalesce(c_rank <= 20, false)::DOUBLE) AS c_recall,
       coalesce(1.0/min(global_rank) FILTER (WHERE global_rank <= 20), 0) AS global_mrr,
       coalesce(1.0/min(recent_rank) FILTER (WHERE recent_rank <= 20), 0) AS recent_mrr,
       coalesce(1.0/min(repeat_rank) FILTER (WHERE repeat_rank <= 20), 0) AS repeat_mrr,
       coalesce(1.0/min(r_rank) FILTER (WHERE r_rank <= 20), 0) AS r_mrr,
       coalesce(1.0/min(ra_rank) FILTER (WHERE ra_rank <= 20), 0) AS ra_mrr,
       coalesce(1.0/min(c_rank) FILTER (WHERE c_rank <= 20), 0) AS c_mrr
FROM matched GROUP BY session;
