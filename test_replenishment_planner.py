import pandas as pd
from replenishment_planner import build_planner, build_audit

BASE_ROW = {
    "facility_id": "F1", "category_name": "C", "manufacturername": "M", "facility_name": "FC",
    "jpin": "SKU", "title": "T", "pvname": "PV", "vendor_lead_time": 2, "inv_norm": 5, "safety_stock": 1,
    "vendor_id": "V1", "vendor_name": "Vendor", "current_vendor_mov": 0, "minimum_order_criteria": "VALUE",
    "max_allocated_space": 1000, "case_size": 10, "cases_allocated": 100, "space_value": 1000,
    "current_inventory": 0, "inventory_breakup": "{}", "max_drr": 3, "deadweight": 1,
    "earliest_promise_date": "", "open_po_details": "{}", "orderedquantity": 0, "open_po_value": 0,
    "open_po_cases": 0, "final_suggestion": 0, "final_days_of_inventory": 0,
    "final_cases_suggestion": 0, "final_value": 0, "final_tonnage": 0, "mov_check": 0,
    "mrp": 20, "cp": 10, "sales_band": "Band A",
}


def row(**overrides):
    r = dict(BASE_ROW)
    r.update(overrides)
    return pd.DataFrame([r])


def test_case_rounding():
    # need = (5+1)*3 = 18 units -> ceil(18/10) = 2 cases = 20 units
    out = build_planner(row(current_inventory=0)).iloc[0]
    assert out.final_suggestion == 20
    assert out.final_cases_suggestion == 2


def test_open_po_reduces_order():
    out = build_planner(row(current_inventory=10, orderedquantity=10)).iloc[0]
    assert out.final_suggestion == 0
    assert out.mov_check == "NOT_REQUIRED"


def test_space_cap_actually_binds():
    # need = 18 units -> 2 cases, but only 1 case (10 units) fits in space
    out = build_planner(row(max_allocated_space=15, case_size=10)).iloc[0]
    assert out.final_suggestion == 10
    assert out.final_cases_suggestion == 1
    assert out.final_suggestion <= 15


def test_mov_is_raised_to_meet_minimum_when_space_allows():
    # need = 18 units -> 2 cases -> value = 20*10 = 200, below MOV of 500.
    # MOV requires ceil(500/(10*10)) = 5 cases = 500 units = 5000 value.
    # Space allows up to 100 cases, so the order SHOULD be bumped to 5 cases.
    out = build_planner(row(current_vendor_mov=500, minimum_order_criteria="VALUE")).iloc[0]
    assert out.final_cases_suggestion == 5
    assert out.mov_check == "PASS"


def test_mov_not_met_maximizes_to_available_space():
    # Same MOV requirement (5 cases) but space only fits 3 cases (30 units).
    # Order should still be pushed to the max feasible (3 cases), not
    # left at the smaller inventory-norm figure.
    out = build_planner(row(
        current_vendor_mov=500, minimum_order_criteria="VALUE",
        max_allocated_space=35, case_size=10,
    )).iloc[0]
    assert out.final_cases_suggestion == 3
    assert out.mov_check == "MOV_NOT_MET_SPACE_LIMIT"


def test_zero_demand_sku_gets_no_order_and_blank_doi():
    out = build_planner(row(max_drr=0, current_inventory=5)).iloc[0]
    assert out.final_suggestion == 0
    assert out.mov_check == "NOT_REQUIRED"
    assert pd.isna(out.final_days_of_inventory)


def test_no_duplicate_output_columns():
    out = build_planner(row())
    assert out.columns.is_unique
    assert list(out.columns).count("final_suggestion") == 1
    assert len(out.columns) == 36


def test_audit_has_no_duplicate_columns_and_extra_diagnostics():
    audit = build_audit(row())
    assert audit.columns.is_unique
    assert "mov_required_cases" in audit.columns
    assert "max_feasible_cases" in audit.columns


if __name__ == "__main__":
    test_case_rounding()
    test_open_po_reduces_order()
    test_space_cap_actually_binds()
    test_mov_is_raised_to_meet_minimum_when_space_allows()
    test_mov_not_met_maximizes_to_available_space()
    test_zero_demand_sku_gets_no_order_and_blank_doi()
    test_no_duplicate_output_columns()
    test_audit_has_no_duplicate_columns_and_extra_diagnostics()
    print("All tests passed.")
