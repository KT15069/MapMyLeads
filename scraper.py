import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def get_sentiment(rating):
    """Compute sentiment label from a numeric rating."""
    try:
        r = float(rating)
        if r >= 4.0:
            return "Positive"
        elif r >= 3.0:
            return "Neutral"
        elif r > 0:
            return "Negative"
    except (TypeError, ValueError):
        pass
    return "Unknown"


def scrape_google_maps(query, location, max_results=20, min_rating=None, min_reviews=None):
    from airtable import get_leads

    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY is not set in .env")

    # ── Build duplicate-check set from existing records ───────────────────────
    existing_records = get_leads()
    existing_keys = set()
    for record in existing_records:
        name    = record.get("fields", {}).get("Name", "").strip()
        address = record.get("fields", {}).get("Address", "").strip()
        existing_keys.add(f"{name}|{address}".lower())

    skipped_duplicates = 0
    qualifying_leads   = []
    start              = 0          # SerpApi pagination offset

    combined_query = f"{query} {location}".strip()

    print(f"[scraper] Searching SerpApi: q='{combined_query}' | max={max_results} | min_rating={min_rating} | min_reviews={min_reviews}")

    while len(qualifying_leads) < max_results:
        params = {
            "engine":  "google_maps",
            "q":       combined_query,
            "type":    "search",
            "api_key": SERPAPI_KEY,
            "start":   start,
        }

        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=30
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"SerpApi HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error contacting SerpApi: {e}")

        data = response.json()

        # SerpApi may return an error field even on HTTP 200
        if "error" in data:
            raise RuntimeError(f"SerpApi error: {data['error']}")

        local_results = data.get("local_results", [])
        print(f"[scraper]   start={start} → {len(local_results)} raw results from SerpApi")

        if not local_results:
            break   # no more pages

        for item in local_results:
            if len(qualifying_leads) >= max_results:
                break

            name = (item.get("title") or "").strip()
            if not name:
                continue

            # Safely parse rating/reviews (may be string or numeric)
            try:
                rating = float(item.get("rating") or 0)
            except (TypeError, ValueError):
                rating = 0.0

            try:
                reviews = int(item.get("reviews") or 0)
            except (TypeError, ValueError):
                reviews = 0

            address = (item.get("address") or "").strip()

            # ── Apply optional filters ───────────────────────────────────────
            if min_rating is not None:
                if rating < float(min_rating):
                    print(f"[scraper]     SKIP '{name}' rating {rating} < {min_rating}")
                    continue

            if min_reviews is not None:
                if reviews < int(min_reviews):
                    print(f"[scraper]     SKIP '{name}' reviews {reviews} < {min_reviews}")
                    continue

            # ── Duplicate check ──────────────────────────────────────────────
            key = f"{name}|{address}".lower()
            if key in existing_keys:
                skipped_duplicates += 1
                print(f"[scraper]     DUP  '{name}'")
                continue

            # ── Build lead dict ──────────────────────────────────────────────
            # 'type' can be str or list depending on listing
            raw_type = item.get("type") or ""
            if isinstance(raw_type, list):
                category = ", ".join(raw_type)
            else:
                category = str(raw_type).strip()

            phone   = (item.get("phone")      or "").strip()
            website = (item.get("website")    or "").strip()
            hours   = (item.get("open_state") or "").strip()

            lead = {
                "Name":     name,
                "Category": category  or None,
                "Address":  address   or None,
                "Phone":    phone     or None,
                "Website":  website   or None,
                "Hours":    hours     or None,
                "Rating":   rating    if rating else None,
                "Reviews":  reviews   if reviews else None,
                "Sentiment": get_sentiment(rating),
                # NOTE: "Scraped Date/Time" is a createdTime field in Airtable.
                # Airtable sets it automatically on record creation — do NOT write it.
            }

            # Strip None values (Airtable rejects nulls in POST)
            lead = {k: v for k, v in lead.items() if v is not None}

            qualifying_leads.append(lead)
            existing_keys.add(key)
            print(f"[scraper]     OK   '{name}' ⭐{rating}")

        # ── Pagination ────────────────────────────────────────────────────────
        pagination = data.get("serpapi_pagination", {})
        if pagination.get("next") and len(local_results) >= 20:
            start += 20
        else:
            break   # no next page

    print(f"[scraper] Done: {len(qualifying_leads)} qualifying leads, {skipped_duplicates} duplicates skipped")
    return qualifying_leads, skipped_duplicates
