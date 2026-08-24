-- Jumbotail Replenishment Planner
-- Suggestion generation date: 2026-03-16
-- SQLite compatible

-- Query 1: Vendor-level dashboard summary
SELECT
    vendor_id,
    vendor_name,
    COUNT(DISTINCT jpin) AS sku_count,
    SUM(final_suggestion) AS suggested_units,
    SUM(final_cases_suggestion) AS suggested_cases,
    ROUND(SUM(final_value), 2) AS suggested_value,
    ROUND(AVG(final_days_of_inventory), 2) AS avg_projected_doi,
    SUM(CASE WHEN mov_check = 'PASS' THEN 1 ELSE 0 END) AS mov_pass_skus,
    SUM(CASE WHEN mov_check = 'MOV_NOT_MET_SPACE_LIMIT' THEN 1 ELSE 0 END) AS mov_space_exceptions
FROM replenishment_data
GROUP BY vendor_id, vendor_name
ORDER BY suggested_value DESC;

-- Query 2: Top 10 riskiest SKUs — lowest DOI where max_drr > 0
SELECT
    facility_id,
    facility_name,
    vendor_id,
    vendor_name,
    jpin,
    title,
    category_name,
    max_drr,
    current_inventory,
    ROUND(CAST(current_inventory AS REAL) / max_drr, 2) AS current_days_of_inventory
FROM replenishment_data
WHERE max_drr > 0
ORDER BY current_days_of_inventory ASC
LIMIT 10;

-- Bonus: Sales-band / inventory-health prioritization
SELECT
    sales_band,
    COUNT(DISTINCT jpin) AS sku_count,
    SUM(final_suggestion) AS suggested_units,
    ROUND(SUM(final_value), 2) AS suggested_value,
    ROUND(AVG(final_days_of_inventory), 2) AS avg_projected_doi,
    SUM(CASE WHEN mov_check = 'MOV_NOT_MET_SPACE_LIMIT' THEN 1 ELSE 0 END) AS exceptions
FROM replenishment_data
GROUP BY sales_band
ORDER BY CASE sales_band
    WHEN 'Band A' THEN 1
    WHEN 'Band B' THEN 2
    WHEN 'Band C' THEN 3
    ELSE 4 END;
