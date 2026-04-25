import os
import requests
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_API_KEY   = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID   = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

if not all([AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME]):
    raise EnvironmentError(
        "Missing Airtable env vars. Check AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME in .env"
    )

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
HEADERS  = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type":  "application/json",
}

# ── Fields the scraper is allowed to WRITE (must match Airtable exactly) ────────
# "Scraped Date/Time" is a createdTime field — Airtable sets it automatically.
# DO NOT include it here or Airtable returns 422.
# "Reach out Stage " has a trailing space — that's the real Airtable field name.
ALLOWED_FIELDS = {
    "Name", "Category", "Address", "Website", "Phone",
    "Email", "Rating", "Reviews", "Sentiment", "Hours", "Notes",
}

VALID_SENTIMENTS = {"Positive", "Neutral", "Negative", "Unknown"}


def _sanitize_lead(lead: dict) -> dict:
    """
    Ensure every value has the correct type before sending to Airtable.
    Drops any field not in ALLOWED_FIELDS to avoid 422 on unknown columns.
    """
    clean = {}
    for key, val in lead.items():
        if key not in ALLOWED_FIELDS:
            print(f"[airtable] WARNING: dropping unknown field '{key}'")
            continue
        if val is None or val == "":
            continue  # skip nulls / empty strings

        if key == "Rating":
            # Airtable 'rating' type = integer 1–5 only. Floats (e.g. 4.2) cause 422.
            try:
                r = round(float(val))
                if 1 <= r <= 5:
                    clean[key] = r
                elif r > 5:
                    clean[key] = 5
                elif r < 1 and r > 0:
                    clean[key] = 1
                # else rating is 0 — omit it (no rating)
            except (TypeError, ValueError):
                pass

        elif key == "Reviews":
            try:
                clean[key] = int(val)
            except (TypeError, ValueError):
                pass

        elif key == "Sentiment":
            clean[key] = val if val in VALID_SENTIMENTS else "Unknown"

        elif key == "Website":
            # Airtable url type — strip whitespace, ensure non-empty
            v = str(val).strip()
            if v:
                clean[key] = v

        else:
            # All other fields are plain text — coerce to str
            clean[key] = str(val).strip()

    return clean


def get_leads():
    """Fetch all records from Airtable with pagination."""
    all_records = []
    params = {}

    while True:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        all_records.extend(data.get("records", []))

        offset = data.get("offset")
        if not offset:
            break
        params = {"offset": offset}

    return all_records


def save_leads(leads: list) -> list:
    """Sanitize and batch-POST leads to Airtable (≤10 per request)."""
    if not leads:
        return []

    records = [{"fields": _sanitize_lead(lead)} for lead in leads]

    # Drop records that were completely empty after sanitization
    records = [r for r in records if r["fields"].get("Name")]

    results = []
    for i in range(0, len(records), 10):
        chunk = records[i: i + 10]
        print(f"[airtable] POSTing {len(chunk)} records to Airtable…")
        print(f"[airtable] Sample fields: {list(chunk[0]['fields'].keys())}")

        response = requests.post(
            BASE_URL,
            json={"records": chunk},
            headers=HEADERS,
            timeout=30,
        )

        if not response.ok:
            # Print the full Airtable error body so we can diagnose 422 etc.
            print(f"[airtable] ❌ HTTP {response.status_code}: {response.text}")
            response.raise_for_status()

        results.extend(response.json().get("records", []))

    return results


def update_lead(record_id: str, notes: str) -> dict:
    """Update only the Notes field of an Airtable record."""
    url = f"{BASE_URL}/{record_id}"
    response = requests.patch(
        url,
        json={"fields": {"Notes": notes}},
        headers=HEADERS,
        timeout=30,
    )

    if not response.ok:
        print(f"[airtable] ❌ PATCH {response.status_code}: {response.text}")
        response.raise_for_status()

    return response.json()
