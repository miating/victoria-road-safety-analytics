-- Question: How do drivers, passengers, motorcyclists, cyclists and pedestrians compare in how
--           often they are killed or seriously injured when involved in a crash?
-- Techniques: GROUP BY, conditional aggregation, window share, RANK, rate per 1,000 people

SELECT ru.road_user_type_desc,
       count(*)                                                                    AS people,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                          AS share_of_people_pct,
       count(*) FILTER (WHERE il.injury_level_code = 1)                            AS killed,
       round(100.0 * count(*) FILTER (WHERE il.injury_level_code = 1)
             / sum(count(*) FILTER (WHERE il.injury_level_code = 1)) OVER (), 1)   AS share_of_deaths_pct,
       round(1000.0 * count(*) FILTER (WHERE il.injury_level_code = 1) / count(*), 1) AS killed_per_1000,
       round(100.0 * count(*) FILTER (WHERE il.injury_level_code IN (1, 2)) / count(*), 1) AS ksi_pct,
       RANK() OVER (ORDER BY count(*) FILTER (WHERE il.injury_level_code IN (1, 2))::NUMERIC / count(*) DESC)
                                                                                   AS ksi_rank
FROM analytics.fact_person fp
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_road_user_type ru USING (road_user_type_key)
JOIN analytics.dim_injury_level il USING (injury_level_key)
WHERE d.is_analysis_period
GROUP BY ru.road_user_type_desc, ru.sort_order
ORDER BY ksi_pct DESC;
