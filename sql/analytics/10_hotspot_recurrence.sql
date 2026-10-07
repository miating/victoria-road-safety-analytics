-- Question: At the ten worst locations of 2020-2024, how often did crashes recur?
-- Approach: for each crash, find the date of the next crash at the same location with LEAD, then
--           take the median gap in days.
-- Techniques: CTE with ORDER BY/LIMIT, IN subquery, LEAD window partitioned by location,
--             ordered-set aggregate percentile_cont

WITH top_locations AS (
    SELECT f.location_key
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    WHERE d.year BETWEEN 2020 AND 2024
      AND f.location_key <> -1
    GROUP BY f.location_key
    ORDER BY count(*) DESC
    LIMIT 10
),
crash_sequence AS (
    SELECT f.location_key,
           d.full_date,
           LEAD(d.full_date) OVER (PARTITION BY f.location_key ORDER BY d.full_date, f.accident_no)
               AS next_crash_date
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    WHERE d.year BETWEEN 2020 AND 2024
      AND f.location_key IN (SELECT location_key FROM top_locations)
)
SELECT l.location_label,
       l.lga_name,
       count(*)                                                                    AS crashes,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY next_crash_date - full_date)    AS median_days_between,
       min(next_crash_date - full_date)                                            AS shortest_gap_days,
       max(next_crash_date - full_date)                                            AS longest_gap_days
FROM crash_sequence c
JOIN analytics.dim_location l USING (location_key)
GROUP BY l.location_key, l.location_label, l.lga_name
ORDER BY median_days_between;
