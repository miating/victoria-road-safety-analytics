-- Question: For people travelling in or on each type of vehicle, how often were they themselves
--           killed or seriously injured?
-- Grain: one row per person (fact_person), grouped by the vehicle they were in. This answers
--        "who gets hurt" rather than query 15's "which vehicles are involved".
-- Techniques: JOIN across three dimensions, conditional aggregation, HAVING, RANK

SELECT vt.vehicle_category,
       count(*)                                                                    AS people,
       count(*) FILTER (WHERE il.injury_level_code = 1)                            AS killed,
       count(*) FILTER (WHERE il.injury_level_code IN (1, 2))                      AS killed_or_seriously_injured,
       round(100.0 * count(*) FILTER (WHERE il.injury_level_code IN (1, 2)) / count(*), 1) AS ksi_pct,
       RANK() OVER (ORDER BY count(*) FILTER (WHERE il.injury_level_code IN (1, 2))::NUMERIC / count(*) DESC)
                                                                                   AS ksi_rank
FROM analytics.fact_person fp
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_vehicle_type vt USING (vehicle_type_key)
JOIN analytics.dim_injury_level il USING (injury_level_key)
WHERE d.is_analysis_period
GROUP BY vt.vehicle_category
HAVING count(*) >= 100
ORDER BY ksi_pct DESC;
