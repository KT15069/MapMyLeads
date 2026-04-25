import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from scraper import scrape_google_maps
from airtable import get_leads, save_leads, update_lead

app = FastAPI(title="MapMyLeads API")

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(BASE_DIR, "public")


class ScrapeRequest(BaseModel):
    query: str
    location: str
    max_results: int = 20
    min_rating: Optional[float] = None
    min_reviews: Optional[int] = None


class UpdateLeadRequest(BaseModel):
    notes: str


@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_path = os.path.join(public_dir, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/scrape")
async def api_scrape(req: ScrapeRequest):
    try:
        new_leads, skipped_duplicates = scrape_google_maps(
            query=req.query,
            location=req.location,
            max_results=req.max_results,
            min_rating=req.min_rating,
            min_reviews=req.min_reviews
        )
        saved_records = []
        if new_leads:
            saved_records = save_leads(new_leads)
        return {
            "success": True,
            "count": len(new_leads),
            "leads": new_leads,
            "savedRecords": saved_records,
            "skipped_duplicates": skipped_duplicates,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "leads": [], "count": 0}


@app.get("/api/leads")
async def api_get_leads():
    try:
        leads = get_leads()
        return {"success": True, "leads": leads}
    except Exception as e:
        return {"success": False, "error": str(e), "leads": []}


@app.patch("/api/leads/{record_id}")
async def api_update_lead(record_id: str, req: UpdateLeadRequest):
    try:
        result = update_lead(record_id, req.notes)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/stats")
async def api_get_stats():
    try:
        leads = get_leads()
        total_leads = len(leads)
        sentiment_counts = {"Positive": 0, "Neutral": 0, "Negative": 0, "Unknown": 0}
        category_counts = {}

        for record in leads:
            fields = record.get("fields", {})
            sent = fields.get("Sentiment", "Unknown")
            if sent in sentiment_counts:
                sentiment_counts[sent] += 1
            else:
                sentiment_counts["Unknown"] += 1

            cat = fields.get("Category", "")
            if cat and cat.strip():
                category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "success": True,
            "total_leads": total_leads,
            "sentiment_counts": sentiment_counts,
            "category_counts": category_counts
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Serve static files (must be after route definitions)
app.mount("/public", StaticFiles(directory=public_dir), name="public")
