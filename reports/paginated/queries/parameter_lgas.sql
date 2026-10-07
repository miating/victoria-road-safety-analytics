-- Values for the LGA parameter: current LGA names, without Unknown and the alpine resorts.
SELECT DISTINCT CASE WHEN lga_name = 'MORELAND' THEN 'MERRI-BEK' ELSE lga_name END AS lga_name
FROM analytics.dim_location
WHERE lga_name <> 'Unknown'
  AND lga_name NOT LIKE '(%'
ORDER BY lga_name;
