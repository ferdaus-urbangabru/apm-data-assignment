import json, math, sqlite3, sys
import numpy as np
import pandas as pd

START_DATE = pd.Timestamp("2026-03-16")

def parse_json(s):
    if pd.isna(s) or not str(s).strip():
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def po_items(s):
    return list(parse_json(s).values())

def mov_required_cases(row):
    mov = max(float(row["current_vendor_mov"] or 0), 0)
    case_size = max(int(row["case_size"] or 1), 1)
    cp = max(float(row["cp"] or 0), 0)
    wt = max(float(row["deadweight"] or 0), 0)
    crit = str(row["minimum_order_criteria"]).upper().strip()
    if mov <= 0:
        return 0
    if crit == "VALUE":
        return math.ceil(mov / (cp * case_size)) if cp > 0 else math.inf
    if crit == "CASES":
        return math.ceil(mov)
    if crit == "TONNAGE":
        return math.ceil(mov / (wt * case_size)) if wt > 0 else math.inf
    return 0

def build_planner(df):
    df = df.copy()
    df["_parsed_po_units"] = df["open_po_details"].apply(
        lambda s: sum(float(x.get("orderedquantity") or 0) for x in po_items(s))
    )
    df["_open_po_units"] = pd.to_numeric(df["orderedquantity"], errors="coerce").fillna(0)

    results = []
    for _, r in df.iterrows():
        drr = max(float(r["max_drr"] or 0), 0)
        on_hand = max(float(r["current_inventory"] or 0), 0)
        open_po = max(float(r["_open_po_units"] or 0), 0)
        target_doi = max(float(r["inv_norm"] or 0), 0) + max(float(r["safety_stock"] or 0), 0)
        target_units = target_doi * drr
        raw_need = max(target_units - on_hand - open_po, 0)

        case_size = max(int(r["case_size"] or 1), 1)
        max_feasible_cases = math.floor(max(float(r["max_allocated_space"] or 0), 0) / case_size)
        required_cases = math.ceil(raw_need / case_size) if raw_need > 0 else 0
        mov_cases = mov_required_cases(r)

        if required_cases == 0:
            order_cases, status = 0, "NOT_REQUIRED"
        else:
            order_cases = min(required_cases, max_feasible_cases)
            if order_cases == 0:
                status = "SPACE_LIMIT"
            elif mov_cases <= order_cases:
                status = "PASS"
            else:
                status = "MOV_NOT_MET_SPACE_LIMIT"

        units = int(order_cases * case_size)
        value = units * max(float(r["cp"] or 0), 0)
        tonnage = units * max(float(r["deadweight"] or 0), 0)
        projected = (on_hand + open_po + units) / drr if drr > 0 else np.nan

        results.append({
            "final_suggestion": units,
            "final_days_of_inventory": round(projected, 2) if pd.notna(projected) else np.nan,
            "final_cases_suggestion": order_cases,
            "final_value": round(value, 2),
            "final_tonnage": round(tonnage, 4),
            "mov_check": status,
        })

    result = pd.concat([df, pd.DataFrame(results, index=df.index)], axis=1)
    return result.drop(columns=["_parsed_po_units", "_open_po_units"])

if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "assignment_data.csv"
    result = build_planner(pd.read_csv(source))
    result.to_csv("replenishment_output.csv", index=False)
    conn = sqlite3.connect("replenishment.db")
    result.to_sql("replenishment_data", conn, if_exists="replace", index=False)
    conn.close()
    print("Planning date:", START_DATE.date())
    print("Rows:", len(result))
    print("Created replenishment_output.csv and replenishment.db")
