import pandas as pd
from replenishment_planner import build_planner

def test_case_rounding_and_space():
    d = pd.DataFrame([{
        "facility_id":"F1","category_name":"C","manufacturername":"M","facility_name":"FC",
        "jpin":"SKU1","title":"T","pvname":"PV","vendor_lead_time":2,"inv_norm":5,"safety_stock":1,
        "vendor_id":"V1","vendor_name":"Vendor","current_vendor_mov":0,"minimum_order_criteria":"VALUE",
        "max_allocated_space":25,"case_size":10,"cases_allocated":2,"space_value":100,
        "current_inventory":0,"inventory_breakup":"{}","max_drr":3,"deadweight":1,
        "earliest_promise_date":"","open_po_details":"{}","orderedquantity":0,"open_po_value":0,
        "open_po_cases":0,"final_suggestion":0,"final_days_of_inventory":0,
        "final_cases_suggestion":0,"final_value":0,"final_tonnage":0,"mov_check":0,
        "mrp":20,"cp":10,"sales_band":"Band A"
    }])
    out = build_planner(d).iloc[0]
    assert out.final_suggestion == 20
    assert out.final_cases_suggestion == 2
    assert out.final_suggestion <= out.max_allocated_space

def test_open_po_reduces_order():
    d = pd.DataFrame([{
        "facility_id":"F1","category_name":"C","manufacturername":"M","facility_name":"FC",
        "jpin":"SKU2","title":"T","pvname":"PV","vendor_lead_time":2,"inv_norm":5,"safety_stock":1,
        "vendor_id":"V1","vendor_name":"Vendor","current_vendor_mov":0,"minimum_order_criteria":"VALUE",
        "max_allocated_space":100,"case_size":10,"cases_allocated":10,"space_value":100,
        "current_inventory":10,"inventory_breakup":"{}","max_drr":3,"deadweight":1,
        "earliest_promise_date":"2026-03-20","open_po_details":"{}","orderedquantity":10,"open_po_value":100,
        "open_po_cases":1,"final_suggestion":0,"final_days_of_inventory":0,
        "final_cases_suggestion":0,"final_value":0,"final_tonnage":0,"mov_check":0,
        "mrp":20,"cp":10,"sales_band":"Band A"
    }])
    out = build_planner(d).iloc[0]
    assert out.final_suggestion == 0

if __name__ == "__main__":
    test_case_rounding_and_space()
    test_open_po_reduces_order()
    print("All tests passed.")
