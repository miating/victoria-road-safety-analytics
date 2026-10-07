-- Year totals for one LGA against the previous year, with the Victorian KSI share for context.
-- Parameters (ODBC placeholders, in order): 1 = LGA name, 2 = report year.
WITH params AS (
    SELECT CAST(? AS text) AS lga, CAST(? AS integer) AS report_year
),
crashes AS (
    SELECT d.year,
           CASE WHEN l.lga_name = 'MORELAND' THEN 'MERRI-BEK' ELSE l.lga_name END = p.lga AS in_lga,
           s.is_fatal_or_serious,
           f.persons_killed
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_location l USING (location_key)
    JOIN analytics.dim_severity s USING (severity_key)
    CROSS JOIN params p
    WHERE d.year IN (p.report_year, p.report_year - 1)
)
SELECT count(*) FILTER (WHERE in_lga AND year = p.report_year)                                  AS crashes,
       count(*) FILTER (WHERE in_lga AND year = p.report_year - 1)                              AS prev_crashes,
       count(*) FILTER (WHERE in_lga AND year = p.report_year AND is_fatal_or_serious)          AS ksi_crashes,
       count(*) FILTER (WHERE in_lga AND year = p.report_year - 1 AND is_fatal_or_serious)      AS prev_ksi_crashes,
       coalesce(sum(persons_killed) FILTER (WHERE in_lga AND year = p.report_year), 0)          AS persons_killed,
       coalesce(sum(persons_killed) FILTER (WHERE in_lga AND year = p.report_year - 1), 0)      AS prev_persons_killed,
       round(100.0 * count(*) FILTER (WHERE year = p.report_year AND is_fatal_or_serious)
             / nullif(count(*) FILTER (WHERE year = p.report_year), 0), 1)                     AS victoria_ksi_share_pct,
       bool_and(d.is_analysis_period)                                                           AS years_complete
FROM crashes
CROSS JOIN params p
CROSS JOIN LATERAL (
    SELECT bool_and(is_analysis_period) AS is_analysis_period
    FROM analytics.dim_date
    WHERE year IN (p.report_year, p.report_year - 1)
) d
GROUP BY p.report_year;
