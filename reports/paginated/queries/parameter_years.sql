-- Values for the year parameter: complete years that also have a complete previous year.
SELECT year
FROM analytics.dim_date
GROUP BY year
HAVING bool_and(is_analysis_period)
   AND year - 1 IN (SELECT year FROM analytics.dim_date GROUP BY year HAVING bool_and(is_analysis_period))
ORDER BY year DESC;
