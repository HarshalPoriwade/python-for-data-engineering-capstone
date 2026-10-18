"""VendRoute: import vending machine sales and print restock advice.

Arguments: SALES_JSON DATABASE [REPORT_JSON]
"""

import json
import os
import sqlite3
import sys

import reports
import storage
import validator

DEFAULT_REPORT_PATH = "vendroute_report.json"


def print_validation(total, rejected):
    print("== Validation report ==")
    print("Read " + str(total) + " sales lines: "
          + str(total - len(rejected)) + " valid, "
          + str(len(rejected)) + " rejected")
    for r in rejected:
        print("  line " + str(r["line"]) + ": " + r["reason"])


def print_revenue(revenue):
    print("== Revenue per machine ==")
    if not revenue:
        print("  (no sales stored yet)")
    for r in revenue:
        word = "item" if r["items"] == 1 else "items"
        print("Machine " + r["machine"] + ": " + str(r["items"]) + " " + word
              + ", revenue " + reports.format_dollars(r["revenue_cents"]))


def print_anomalies(anomalies):
    print("== Price anomalies (more than "
          + str(reports.ANOMALY_LIMIT_PERCENT) + "% from usual price) ==")
    if not anomalies:
        print("  none found")
    for a in anomalies:
        print("  Machine " + a["machine"] + ", " + a["item"]
              + " on " + a["date"]
              + ": recorded " + reports.format_dollars(a["recorded_cents"])
              + ", expected " + reports.format_dollars(a["expected_cents"]))


def print_restock(notes):
    print("== Restock notes ==")
    if not notes:
        print("  (nothing to restock)")
    for machine, lines in notes.items():
        print("Machine " + machine + ":")
        for line in lines:
            print("  - " + line["item"] + ": sold "
                  + reports.format_quantity(line["sold"])
                  + ", restock " + str(line["restock"]))


def write_report(report, report_path):
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def run(json_path, db_path, report_path):
    """Do the whole import and return the exit code."""
    try:
        records = validator.load_records(json_path)
    except validator.SalesFileError as e:
        print("Error: " + str(e))
        return 1

    valid, rejected = validator.validate_records(records)
    print_validation(len(records), rejected)

    try:
        conn = storage.connect(db_path)
        try:
            inserted = storage.insert_sales(conn, valid)
            sales = storage.fetch_sales(conn)
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        # Also covers OperationalError, e.g. a folder that does not exist.
        print("Error: cannot use database " + db_path + ": " + str(e))
        return 1
    print("Inserted " + str(inserted) + " new sales lines ("
          + str(len(valid) - inserted) + " skipped as duplicates)")
    print()

    report = reports.build_report(rejected, inserted, sales)
    print_revenue(report["revenue"])
    print()
    print_anomalies(report["anomalies"])
    print()
    print_restock(report["restock"])
    print()

    try:
        write_report(report, report_path)
    except OSError as e:
        reason = e.strerror or str(e)
        print("Error: cannot write report " + report_path + ": " + reason)
        return 1
    print("Report saved to " + report_path)
    return 0


def main(argv):
    if len(argv) < 3 or len(argv) > 4:
        program = os.path.basename(argv[0])
        print("Usage: python " + program + " SALES_JSON DATABASE [REPORT_JSON]")
        return 1
    report_path = argv[3] if len(argv) == 4 else DEFAULT_REPORT_PATH
    return run(argv[1], argv[2], report_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

