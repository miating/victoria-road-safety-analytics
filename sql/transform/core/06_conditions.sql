-- Multi-valued crash conditions: one row per crash and condition.

INSERT INTO core.crash_atmospheric_cond (accident_no, atmosph_cond_code, sequence_no)
SELECT t.accident_no, t.atmosph_cond::SMALLINT, t.atmosph_cond_seq::SMALLINT
FROM staging.atmospheric_cond t
JOIN core.crash c ON c.accident_no = t.accident_no
WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'atmospheric_cond' AND r.source_row_number = t.source_row_number);

INSERT INTO core.crash_surface_cond (accident_no, surface_cond_code, sequence_no)
SELECT t.accident_no, t.surface_cond::SMALLINT, t.surface_cond_seq::SMALLINT
FROM staging.road_surface_cond t
JOIN core.crash c ON c.accident_no = t.accident_no
WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'road_surface_cond' AND r.source_row_number = t.source_row_number);

INSERT INTO core.crash_sub_dca (accident_no, sub_dca_code, sequence_no)
SELECT t.accident_no, t.sub_dca_code, t.sub_dca_seq::SMALLINT
FROM staging.sub_dca t
JOIN core.crash c ON c.accident_no = t.accident_no
WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'sub_dca' AND r.source_row_number = t.source_row_number);
