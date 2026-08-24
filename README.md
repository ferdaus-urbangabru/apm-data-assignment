# Jumbotail Replenishment Planner

## Planning date
**2026-03-16**

## Deliverables
- `assignment_solution.ipynb` — notebook with implementation and validation.
- `replenishment_planner.py` — reproducible Python script.
- `replenishment_output.csv` — 36-column output with all six requested output fields populated.
- `replenishment_audit.csv` — intermediate calculations and checks.
- `replenishment_queries.sql` — schema-ready SQL queries, including the two required queries.
- `replenishment.db` — SQLite database containing `replenishment_data`.
- `test_replenishment_planner.py` — bonus tests for core computations.
- `README.md` — assumptions, run instructions and AI-use notes.
- `assignment_data.csv` — source dataset.

## How to run

```bash
pip install pandas numpy jupyter
python replenishment_planner.py assignment_data.csv
python test_replenishment_planner.py
jupyter notebook assignment_solution.ipynb
```

The script writes `replenishment_output.csv` and `replenishment.db`.

## Core logic

1. **Planning date:** 2026-03-16.
2. Parse `inventory_breakup` and `open_po_details` JSON.
3. Treat `orderedquantity` as the dataset's aggregate open-PO units. The JSON detail is parsed and retained for reconciliation, but it is not assumed complete for every row.
4. Target inventory = (`inv_norm` + `safety_stock`) × `max_drr`.
5. Required new units = max(target inventory − current on-hand − open-PO units, 0).
6. Round the required order **up to whole `case_size` multiples**.
7. Enforce the required **space cap** by limiting the suggested quantity to the largest whole-case quantity ≤ `max_allocated_space`.
8. Enforce MOV:
   - `VALUE`: order value (units × CP) must meet `current_vendor_mov`.
   - `CASES`: order cases must meet `current_vendor_mov`.
   - `TONNAGE`: supported defensively as order tonnage ≥ MOV.
9. If an order is needed but MOV cannot be achieved without exceeding the space cap, place the maximum feasible whole-case order and flag `MOV_NOT_MET_SPACE_LIMIT`. This preserves both the space constraint and transparency about the unavoidable MOV exception.
10. Current DOI = on-hand / DRR when DRR > 0.
11. Projected DOI = (on-hand + open PO + suggested order) / DRR when DRR > 0.
12. Zero-demand SKUs receive no replenishment; DOI is blank where DRR is zero.

## Why open POs are handled this way

The assignment explicitly provides `orderedquantity` as the total units already on order and asks the planner to account for open POs in the pipeline. Therefore all currently open PO units are deducted before calculating the new requirement. The JSON is parsed because the assignment explicitly requires JSON handling, but the aggregate `orderedquantity` is used as the authoritative pipeline total where the detail JSON is incomplete.

## Inventory-health prioritization

The output includes sales-band information and the SQL file contains a bonus sales-band summary. A production version could use Band A/B/C to allocate limited procurement attention, but the core PO calculation remains driven by inventory norms, safety stock, DRR, open POs, cases, space and MOV.

## Validation

- Source rows processed: 1,389
- Note: The assignment description states 1,419 rows, while the provided `assignment_data.csv` contains 1,389 rows; the solution processes the provided dataset as-is.
- Output columns: 36
- Suggested units: 889,103
- Suggested cases: 10,563
- Suggested purchase value: ₹10,299,435.22
- Whole-case constraint: PASS
- Space-cap constraint: PASS
- Non-negative suggestion constraint: PASS
- MOV exceptions caused by space: 708

## SQL

`replenishment_queries.sql` contains:

1. **Vendor-level summary:** total suggested value, cases, units, SKU count, projected DOI and MOV exceptions.
2. **Top 10 riskiest SKUs:** lowest current DOI where `max_drr > 0`, including facility, vendor, title and current DOI.
3. Bonus sales-band inventory-health summary.

## AI usage

AI was expected and was used as an implementation accelerator for:
- translating the assignment requirements into reproducible Python logic;
- JSON parsing and edge-case handling;
- SQL query drafting;
- test-case drafting;
- README/documentation.

I manually verified the key business constraints: planning date, open-PO treatment, target DOI calculation, case rounding, space cap, MOV logic, zero-demand handling, output schema, and the two required SQL queries.

## What I would improve with more time

- Use open-PO promise dates to distinguish POs arriving before/after a planning horizon.
- Add expiry/batch-aware FEFO risk if batch-level expiry data is available.
- Add a Streamlit dashboard for vendor/facility/category drill-down.
- Add richer sales-band prioritization when procurement capacity is constrained.
- Add automated data-quality reconciliation between JSON PO detail and aggregate PO columns.
