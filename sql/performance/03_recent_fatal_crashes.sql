-- Scenario: A "fatal crash register" page lists the 50 most recent fatal crashes.
-- Problem: fatal crashes are 1.7% of rows. Without an index PostgreSQL reads all 200,754
--          crashes, keeps the fatal ones and sorts them by date to find the latest 50.
-- Fix: partial index on core.crash (crash_date DESC) WHERE severity_code = 1. It contains
--      only fatal crashes, already in the required order, so the query reads 50 index entries
--      and stops. The index is a fraction of the size of a full index on crash_date.

SELECT c.accident_no,
       c.crash_date,
       c.crash_time,
       c.persons_killed,
       n.lga_name,
       c.speed_limit_kmh
FROM core.crash c
LEFT JOIN core.node n ON n.node_id = c.node_id
WHERE c.severity_code = 1
ORDER BY c.crash_date DESC, c.crash_time DESC
LIMIT 50;
