import json, math, sqlite3, sys
import numpy as np
import pandas as pd

START_DATE = pd.Timestamp("2026-03-16")

# The 6 output columns already exist (blank) in assignment_data.csv per the
# assignment's 36-column schema. We compute fresh values for them and must
# overwrite -- not duplicate -- these columns in the final output.
OUTPUT_COLUMNS = [
    "final_suggestion",
    "final_days_of_inventory",
    "final_cases_suggestion",
    "final_value",
    "final_tonnage",
    "mov_check",
]


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
    """Minimum whole cases needed to satisfy current_vendor_mov under the
    row's minimum_order_criteria. Returns 0 if no MOV applies, math.inf if
    the MOV can never be reached (e.g. cp/deadweight is 0)."""
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
        # current_vendor_mov is read as a case-count threshold under this
        # criterion (see README "Key assumptions").
        return math.ceil(mov)
    if crit == "TONNAGE":
        return math.ceil(mov / (wt * case_size)) if wt > 0 else math.inf
    # Unrecognized/blank criterion: no MOV enforced (defensive default).
    return 0


def _plan_row(r):
    """Core per-row planning logic. Returns a dict of both the six required
    output fields and the intermediate values used to compute them, so the
    same function can drive both the main output and the audit file."""
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
        # No replenishment need -> never force an order just to hit MOV.
        order_cases, status = 0, "NOT_REQUIRED"
    else:
        # Try to satisfy both the inventory need AND the vendor's MOV,
        # bounded by whatever fits in the allocated space. Even when MOV
        # can't be fully reached, place the maximum feasible whole-case
        # order rather than stopping at the smaller inventory-norm figure.
        desired_cases = max(required_cases, mov_cases) if mov_cases != math.inf else required_cases
        order_cases = min(desired_cases, max_feasible_cases) if max_feasible_cases < math.inf else desired_cases
        order_cases = int(order_cases)

        if order_cases == 0:
            status = "SPACE_LIMIT"
        elif mov_cases == math.inf:
            status = "MOV_UNREACHABLE"
        elif order_cases >= mov_cases:
            status = "PASS"
        else:
            status = "MOV_NOT_MET_SPACE_LIMIT"

    units = int(order_cases * case_size)
    value = units * max(float(r["cp"] or 0), 0)
    tonnage = units * max(float(r["deadweight"] or 0), 0)
    current_doi = on_hand / drr if drr > 0 else np.nan
    projected = (on_hand + open_po + units) / drr if drr > 0 else np.nan

    return {
        "final_suggestion": units,
        "final_days_of_inventory": round(projected, 2) if pd.notna(projected) else np.nan,
        "final_cases_suggestion": order_cases,
        "final_value": round(value, 2),
        "final_tonnage": round(tonnage, 4),
        "mov_check": status,
        # audit-only fields
        "open_po_units_used": open_po,
        "current_doi": round(current_doi, 2) if pd.notna(current_doi) else np.nan,
        "target_doi": target_doi,
        "target_units": round(target_units, 2),
        "raw_need_units": round(raw_need, 2),
        "max_feasible_cases": max_feasible_cases,
        "mov_required_cases": mov_cases if mov_cases != math.inf else np.nan,
        "projected_doi_recalc": round(projected, 2) if pd.notna(projected) else np.nan,
    }


def build_planner(df):
    df = df.copy()
    df["_open_po_units"] = pd.to_numeric(df["orderedquantity"], errors="coerce").fillna(0)

    rows = [_plan_row(r) for _, r in df.iterrows()]
    results = pd.DataFrame(
        [{k: v for k, v in r.items() if k in OUTPUT_COLUMNS} for r in rows],
        index=df.index,
    )

    # Overwrite the pre-existing (blank) output columns instead of
    # concatenating duplicate-named columns onto the DataFrame.
    df = df.drop(columns=[c for c in OUTPUT_COLUMNS if c in df.columns])
    result = pd.concat([df, results], axis=1)
    return result.drop(columns=["_open_po_units"])


def build_audit(df):
    """Row-level intermediate calculations, for reconciliation/debugging."""
    df = df.copy()
    df["_open_po_units"] = pd.to_numeric(df["orderedquantity"], errors="coerce").fillna(0)

    rows = [_plan_row(r) for _, r in df.iterrows()]
    audit_fields = pd.DataFrame(rows, index=df.index)

    df = df.drop(columns=[c for c in OUTPUT_COLUMNS if c in df.columns])
    audit = pd.concat([df, audit_fields], axis=1)
    audit.insert(0, "planning_date", START_DATE.date().isoformat())
    return audit.drop(columns=["_open_po_units"])


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "assignment_data.csv"
    raw = pd.read_csv(source)

    result = build_planner(raw)
    assert result.columns.is_unique, "Output has duplicate column names -- check schema."
    result.to_csv("replenishment_output.csv", index=False)

    audit = build_audit(raw)
    assert audit.columns.is_unique, "Audit output has duplicate column names -- check schema."
    audit.to_csv("replenishment_audit.csv", index=False)

    conn = sqlite3.connect("replenishment.db")
    result.to_sql("replenishment_data", conn, if_exists="replace", index=False)
    conn.close()

    print("Planning date:", START_DATE.date())
    print("Rows:", len(result))
    print("Columns:", len(result.columns))
    print()
    print("mov_check distribution:")
    print(result["mov_check"].value_counts())
    print()
    print("Suggested units:", int(result["final_suggestion"].sum()))
    print("Suggested cases:", int(result["final_cases_suggestion"].sum()))
    print("Suggested value:", round(result["final_value"].sum(), 2))
    print()
    print("Created replenishment_output.csv, replenishment_audit.csv and replenishment.db")
