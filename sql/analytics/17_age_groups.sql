-- Question: Which age groups are most represented among people involved in crashes, and which
--           are most often killed or seriously injured?
-- Techniques: GROUP BY with a sort key from the dimension, window share, conditional aggregation
-- Caveat: counts are not population rates - age groups differ in size and in how much they travel.

SELECT pd.age_group,
       count(*)                                                                    AS people,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                          AS share_pct,
       count(*) FILTER (WHERE il.injury_level_code = 1)                            AS killed,
       round(100.0 * count(*) FILTER (WHERE il.injury_level_code IN (1, 2)) / count(*), 1) AS ksi_pct
FROM analytics.fact_person fp
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_person_demographic pd USING (person_demographic_key)
JOIN analytics.dim_injury_level il USING (injury_level_key)
WHERE d.is_analysis_period
GROUP BY pd.age_group, pd.age_group_sort
ORDER BY pd.age_group_sort;
