-- Monthly performance for one LGA and year, with the same month of the previous year.
-- Parameters (ODBC placeholders, in order): 1 = LGA name, 2 = report year.
-- Moreland was renamed Merri-bek in 2022; both names are reported as MERRI-BEK.
WITH params AS (
    SELECT CAST(? AS text) AS lga, CAST(? AS integer) AS report_year
),
monthly AS (
    SELECT d.year,
           d.month_number,
           count(*)                                         AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious)    AS ksi_crashes,
           sum(f.persons_killed)                            AS persons_killed
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_location l USING (location_key)
    JOIN analytics.dim_severity s USING (severity_key)
    CROSS JOIN params p
    WHERE CASE WHEN l.lga_name = 'MORELAND' THEN 'MERRI-BEK' ELSE l.lga_name END = p.lga
      AND d.year IN (p.report_year, p.report_year - 1)
    GROUP BY d.year, d.month_number
)
SELECT m.month_number,
       to_char(make_date(2000, m.month_number, 1), 'Mon')   AS month_name,
       coalesce(cur.crashes, 0)                             AS crashes,
       coalesce(cur.ksi_crashes, 0)                         AS ksi_crashes,
       coalesce(cur.persons_killed, 0)                      AS persons_killed,
       coalesce(prev.crashes, 0)                            AS prev_crashes,
       coalesce(prev.ksi_crashes, 0)                        AS prev_ksi_crashes
FROM generate_series(1, 12) AS m(month_number)
CROSS JOIN params p
LEFT JOIN monthly cur  ON cur.month_number = m.month_number AND cur.year = p.report_year
LEFT JOIN monthly prev ON prev.month_number = m.month_number AND prev.year = p.report_year - 1
ORDER BY m.month_number;
