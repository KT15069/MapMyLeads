"""
Run this once to see every field name and type in your Airtable table.
Usage: venv\Scripts\python.exe check_schema.py
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("AIRTABLE_API_KEY")
BASE_ID  = os.getenv("AIRTABLE_BASE_ID")
TABLE_ID = os.getenv("AIRTABLE_TABLE_NAME")

headers = {"Authorization": f"Bearer {API_KEY}"}

# ── Method 1: Meta API (gets field types) ─────────────────────────────────────
print("Fetching Airtable schema via meta API...")
meta_url = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"
r = requests.get(meta_url, headers=headers)

if r.status_code == 200:
    tables = r.json().get("tables", [])
    table = next((t for t in tables if t["id"] == TABLE_ID or t["name"] == TABLE_ID), None)
    if table:
        print(f"\n✅ Table: '{table['name']}' ({table['id']})")
        print("   Field name (case-sensitive) → type")
        print("   " + "─" * 50)
        for f in table["fields"]:
            print(f"   \"{f['name']}\"  →  {f['type']}")
    else:
        print(f"❌ Table '{TABLE_ID}' not found. Available tables:")
        for t in tables:
            print(f"   - '{t['name']}' ({t['id']})")
else:
    print(f"Meta API failed ({r.status_code}): {r.text}")
    print("\nFallback: reading first record to guess field names...")
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}?maxRecords=1"
    r2 = requests.get(url, headers=headers)
    if r2.status_code == 200:
        records = r2.json().get("records", [])
        if records:
            print("✅ Fields found in first record:")
            for k, v in records[0]["fields"].items():
                print(f'   "{k}"  =  {repr(v)[:60]}')
        else:
            print("Table is empty — no field names to read.")
    else:
        print(f"Fallback also failed ({r2.status_code}): {r2.text}")
