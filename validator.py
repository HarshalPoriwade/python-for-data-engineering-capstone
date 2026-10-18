"""Load a vending machine sales file and check every sales line."""

import json
import math

REQUIRED_FIELDS = ["machine", "item", "price_cents", "quantity", "date"]
class SalesFileError(Exception):
    """Raised when the sales file cannot be read as a list of sales lines."""


def load_records(json_path):
    """Read the JSON file and return its list of records.

    utf-8-sig also accepts files that start with a byte order mark,
    which some Windows editors add.
    """
    try:
        with open(json_path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except FileNotFoundError:
        raise SalesFileError("file not found: " + json_path)
    except UnicodeDecodeError:
        # Happens when the database file is given where the JSON should be.
        raise SalesFileError("not a JSON text file: " + json_path)
    except OSError as e:
        reason = e.strerror or str(e)
        raise SalesFileError("cannot read " + json_path + ": " + reason)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SalesFileError(
            "malformed JSON in " + json_path + ": " + e.msg
            + " (line " + str(e.lineno) + ", column " + str(e.colno) + ")"
        )

    if not isinstance(data, list):
        raise SalesFileError(
            "expected a JSON list of sales lines in " + json_path
        )
    return data


def is_number(value):
    # bool is a subclass of int in Python, so True would sneak through.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    # json.loads accepts NaN and Infinity, which are not real amounts.
    return math.isfinite(value)


def check_record(record):
    """Return a list of reasons why the record is invalid (empty = valid)."""
    if not isinstance(record, dict):
        return ["record is not a JSON object"]

    reasons = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            reasons.append("missing field '" + field + "'")

    for field in ["machine", "item", "date"]:
        value = record.get(field)
        if value is not None and not isinstance(value, str):
            reasons.append(field + " must be text")

    price = record.get("price_cents")
    if price is not None:
        if not is_number(price) or price != int(price):
            reasons.append("price_cents must be a whole number")
        elif price <= 0:
            reasons.append("price_cents must be positive (got " + str(price) + ")")

    quantity = record.get("quantity")
    if quantity is not None:
        if not is_number(quantity):
            reasons.append("quantity must be a number")
        elif quantity <= 0:
            reasons.append("quantity must be positive (got " + str(quantity) + ")")

    return reasons


def clean_record(record):
    """Return a tidy copy of a valid record with stripped text values."""
    return {
        "machine": record["machine"].strip(),
        "item": record["item"].strip(),
        "price_cents": int(record["price_cents"]),
        "quantity": record["quantity"],
        "date": record["date"].strip(),
    }


def validate_records(records):
    """Split records into (valid, rejected).

    Line numbers start at 1: the first sales line in the file is line 1.
    """
    valid = []
    rejected = []
    for line_number, record in enumerate(records, start=1):
        reasons = check_record(record)
        if reasons:
            rejected.append({"line": line_number, "reason": "; ".join(reasons)})
        else:
            valid.append(clean_record(record))
    return valid, rejected