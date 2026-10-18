"""Build the three VendRoute reports from the stored sales."""

import math

import pandas as pd

ANOMALY_LIMIT_PERCENT = 20


def format_dollars(cents):
    """Turn a whole number of cents into text such as $12.50."""
    cents = int(round(cents))
    return "$" + str(cents // 100) + "." + str(cents % 100).zfill(2)


def format_quantity(quantity):
    """Show 3.0 as 3 but keep 2.5 as 2.5."""
    if quantity == int(quantity):
        return str(int(quantity))
    return str(quantity)


def make_frame(sales):
    """Build a DataFrame with the right columns even when there are no sales."""
    columns = ["machine", "item", "price_cents", "quantity", "date"]
    return pd.DataFrame(sales, columns=columns)


def revenue_per_machine(sales):
    """Return one dict per machine, highest total revenue first."""
    df = make_frame(sales)
    if df.empty:
        return []
    df["revenue_cents"] = df["price_cents"] * df["quantity"]
    grouped = df.groupby("machine").agg(
        items=("item", "nunique"),
        revenue_cents=("revenue_cents", "sum"),
    )
    grouped = grouped.reset_index()
    # Ties on revenue are listed alphabetically so the order never changes.
    grouped = grouped.sort_values(
        by=["revenue_cents", "machine"], ascending=[False, True]
    )
    result = []
    for row in grouped.itertuples(index=False):
        result.append({
            "machine": row.machine,
            "items": int(row.items),
            "revenue_cents": int(round(row.revenue_cents)),
        })
    return result


def expected_prices(sales):
    """Return {item: most common price_cents for that item across all machines}.

    When two prices are equally common, Series.mode() sorts them and we
    take the lowest one.
    """
    df = make_frame(sales)
    expected = {}
    for item, group in df.groupby("item"):
        expected[item] = int(group["price_cents"].mode().iloc[0])
    return expected


def find_anomalies(sales):
    """Return sales whose price differs from the expected price by more than 20%."""
    expected = expected_prices(sales)
    anomalies = []
    for sale in sales:
        normal = expected[sale["item"]]
        difference = abs(sale["price_cents"] - normal)
        # Whole-number maths avoids float rounding right at the 20% edge.
        if difference * 100 > ANOMALY_LIMIT_PERCENT * normal:
            anomalies.append({
                "machine": sale["machine"],
                "item": sale["item"],
                "date": sale["date"],
                "recorded_cents": sale["price_cents"],
                "expected_cents": normal,
            })
    anomalies.sort(key=lambda a: (a["machine"], a["item"], a["date"]))
    return anomalies


def restock_notes(sales):
    """Return {machine: [{item, sold, restock}, ...]} with best sellers first."""
    df = make_frame(sales)
    notes = {}
    if df.empty:
        return notes
    totals = df.groupby(["machine", "item"])["quantity"].sum().reset_index()
    for machine in sorted(totals["machine"].unique()):
        rows = totals[totals["machine"] == machine]
        rows = rows.sort_values(by=["quantity", "item"], ascending=[False, True])
        lines = []
        for row in rows.itertuples(index=False):
            # Rounding first stops a float sum like 3.0000000000000004
            # from being rounded up to 4 units.
            sold = round(float(row.quantity), 6)
            lines.append({
                "item": row.item,
                "sold": int(sold) if sold == int(sold) else sold,
                "restock": math.ceil(sold),
            })
        notes[machine] = lines
    return notes


def build_report(rejected, inserted, sales):
    """Collect everything the operator needs into one dictionary."""
    return {
        "validation": {
            "rejected_count": len(rejected),
            "rejected": rejected,
        },
        "inserted": inserted,
        "revenue": revenue_per_machine(sales),
        "anomalies": find_anomalies(sales),
        "restock": restock_notes(sales),
    }