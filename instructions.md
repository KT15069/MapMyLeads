# Project Specs

## 1. What the user can do:
- Open the web app in a browser and see a full dashboard on the Home page.
- Type a natural language query in the chat bar (e.g. "Find 10 hair salons in Austin with rating above 4.2") to either search existing leads or scrape new ones.
- View all scraped leads in a sortable, filterable table on the Database page.
- Add notes per lead inline in the table, saved on blur.
- Browse all past scrape sessions in the History page.
- Adjust app preferences in Settings.
- View and edit personal info in Profile.

---

## 2. What workflows exist:

1. `scrape_google_maps`
    - Input: `query` (string), `location` (string), `max_results` (integer, default 20), `min_rating` (float, optional), `min_reviews` (integer, optional).
    - Calls SerpApi Google Maps endpoint using `requests`. No browser needed.
    - Filters out any listing below `min_rating` or `min_reviews` if provided.
    - Keeps collecting until exactly `max_results` qualifying leads are found, or results run out.
    - Computes `sentiment` per lead:
        - `rating >= 4.0` → `"Positive"`
        - `rating >= 3.0 and < 4.0` → `"Neutral"`
        - `rating < 3.0` → `"Negative"`
        - rating unavailable → `"Unknown"`
    - Checks duplicates by `Name` + `Address` before saving. Skips existing records.
    - Output: Passes qualifying leads to `airtable_save_leads`.

2. `airtable_save_leads`
    - Batch POSTs leads to Airtable (max 10 per request, loop for more).
    - Uses `requests` for all HTTP calls.
    - Writes only these columns: `Name`, `Category`, `Address`, `Website`, `Phone`, `Email`, `Hours`, `Rating`, `Reviews`, `Sentiment`, `Scraped Date/Time`.
    - Does not write to `Reach Out Stage` or `Follow-up` — those are managed by the user directly in Airtable.

3. `airtable_get_leads`
    - Fetches all records from Airtable and returns them for the frontend table.
    - Returns all columns including `Reach Out Stage` and `Follow-up` for display only (read-only in the app).

4. `airtable_update_lead`
    - Input: `record_id`, `notes`.
    - Only updates the `Notes` field. No other fields are written by the app after initial save.

5. `save_chat_session`
    - After each scrape or search, saves the session to localStorage on the frontend.
    - Fields: `id`, `title` (auto-generated from query), `timestamp`, `lead_count`, `emoji` (auto-picked by category).
    - Used to populate the History page and sidebar history list.

---

## 3. What tools are being used:
- **Python + FastAPI:** Backend server and all API routing. Run with `uvicorn`.
- **requests:** All HTTP calls to SerpApi and Airtable REST API.
- **python-dotenv:** Loads environment variables from `.env`.
- **SerpApi (Google Maps endpoint):** Fetches listings via REST, returns structured JSON.
- **Airtable REST API:** Storing and retrieving leads.
- **Frontend (Vanilla HTML + CSS + JS):** Single `public/index.html`. No framework, no build step. Served as a static file by FastAPI.

---

## 4. What outputs are expected:
- After a scrape: leads appear in the chat as a preview card and are saved to Airtable automatically.
- The Home dashboard shows counts for total leads, sentiment breakdown, and leads per category.
- Database table shows all leads. `Reach Out Stage` and `Follow-up` columns are visible but read-only.
- Notes column is the only column editable in the app.
- History page and sidebar list show all past sessions from localStorage.
- If scrape fails or Airtable is unreachable, a visible error state appears in the chat and UI.

---

## 5. Where data is stored:
- **Airtable**, table name: `Leads`.
- Columns the app writes to: `Name`, `Category`, `Address`, `Website`, `Phone`, `Email`, `Hours`, `Rating`, `Reviews`, `Sentiment`, `Scraped Date/Time`.
- Columns the app reads but never writes: `Reach Out Stage`, `Follow-up`.
- `Sentiment` → Single select: `Positive`, `Neutral`, `Negative`, `Unknown`.
- `Reach Out Stage` → Single select managed by user in Airtable: `Yet to Call`, `Asked to Call Back`, `Showed Interest`, `Interested`, `Not Interested`.
- `Follow-up` → Single select managed by user in Airtable: `1 Week`, `2 Weeks`, `1 Month`, `2 Month`.
- Chat session history → `localStorage` on the frontend (key: `mml_sessions`).

---

## 6. Where the system runs:
- **Locally** via `uvicorn server:app --reload`.
- Secrets in `.env` at project root. Never hardcoded.
- Required `.env` keys: `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`, `SERPAPI_KEY`, `PORT`.

---

## 7. File structure:
```
google-maps-leads/
├── .env
├── .gitignore            # exclude __pycache__/, .env, venv/
├── requirements.txt      # fastapi, uvicorn, requests, python-dotenv
├── server.py             # FastAPI app, all API routes, serves index.html
├── scraper.py            # SerpApi scraping + filter + sentiment logic
├── airtable.py           # Airtable create / get / update helpers
└── public/
    └── index.html        # Full single-file frontend
```

---

## 8. Backend setup instructions:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install fastapi uvicorn requests python-dotenv
pip freeze > requirements.txt
```

Start the server:
```bash
uvicorn server:app --reload --port 3000
```

---

## 9. API endpoints (server.py):

```
POST /api/scrape        body: { query, location, max_results, min_rating, min_reviews }
                        → runs scraper → pushes to Airtable → returns leads array

GET  /api/leads         → fetches all records from Airtable → returns array

PATCH /api/leads/{id}   body: { notes }
                        → updates only the Notes field of a single Airtable record

GET  /api/stats         → returns total lead count, sentiment breakdown, and leads
                          per category. Used by Home dashboard.

GET  /                  → serves public/index.html
```

---

## 10. Frontend — Layout and Pages:

The entire frontend lives in one `public/index.html` file. Fixed left sidebar, main content area on the right. No frameworks. No build step.

### Sidebar (always visible):
- App logo and name `MapMyLeads` at the top.
- `+ New Scrape` button — opens a fresh chat session.
- Nav items (top): `Home`, `History`, `Database`.
- Below nav: scrollable list of recent sessions from localStorage, grouped Today / Yesterday / Earlier.
- Nav items (bottom): `Settings`, `Profile`.
- Active nav item highlighted with amber accent.

### Page 1 — Home:
- Greeting header based on time of day: "Good morning / afternoon / evening".
- Dashboard grid with three cards:
    - **Total Leads card:** Large number showing total leads in Airtable. Data from `GET /api/stats`.
    - **Sentiment Breakdown card:** Count per sentiment — Positive, Neutral, Negative, Unknown. Color-coded dots. Data from `GET /api/stats`.
    - **Lead Categories card (wide):** Horizontal bar chart of lead count per category. Bars animate in on load. Data from `GET /api/stats`.
- Persistent chat input bar at the bottom. On submit, creates a new session in localStorage and navigates to History with the active chat open.

### Page 2 — History:
- Lists all sessions from localStorage, grouped Today / Yesterday / Earlier.
- Each card: emoji icon, title, preview text (e.g. "Scraped 5 leads · Avg rating 4.3"), timestamp, lead count badge.
- Clicking a session opens the chat thread showing the original messages and a leads preview card.

### Page 3 — Database:
- Search bar: filters by name, city, or category (client-side).
- Filter buttons: Positive, Neutral, Negative (toggle by sentiment).
- Sort toggle: cycles Rating ↓ and Reviews ↓.
- Table columns: `Name`, `Category`, `Address`, `Rating`, `Reviews`, `Sentiment`, `Phone`, `Email`, `Website`, `Hours`, `Scraped Date/Time`, `Reach Out Stage` (read-only), `Follow-up` (read-only), `Notes`.
- `Sentiment`: color-coded pill badge — green, amber, red, grey.
- `Reach Out Stage` and `Follow-up`: displayed as plain text badges. Not editable in the app.
- `Notes`: inline editable field. onBlur calls `PATCH /api/leads/{id}`.

### Page 4 — Settings:
- Toggles: Dark mode (default on), Auto-refresh dashboard, Show phone in table.
- Inputs: Default max results, Default min rating.
- Danger zone: Clear localStorage sessions button.

### Page 5 — Profile:
- Avatar circle showing initials.
- Editable fields: Name, Email, Phone. Edit button per field turns it into an input. Saves to localStorage.

---

## 11. Design direction:
- **Theme:** Dark. Background `#0a0a0a`. Surfaces `#111111` and `#1a1a1a`. Borders `rgba(255,255,255,0.07)`.
- **Accent:** Amber `#f5a623`. Used for active nav, buttons, highlights, bar fills.
- **Typography:** `DM Sans` for UI, `Fira Code` for table data cells. Import from Google Fonts.
- **Aesthetic:** Apple-inspired minimal. Generous spacing, subtle borders, no drop shadows, no gradients.
- **Sentiment badges:** Pill shape — green/amber/red/grey with matching background tint.
- **Animations:** Cards fade in with staggered delay on page load. Chat input glows amber on focus.
- **No frameworks, no CDN UI kits.** Pure CSS variables and vanilla JS only.

---

## 12. What "done" looks like:
When the user opens the app:
1. Home dashboard loads with live counts from `GET /api/stats`.
2. User types "Find 5 plumbers in Miami with rating above 4.0" and hits enter.
3. A new chat session is created in localStorage, user is taken to History with the active chat open.
4. App calls `POST /api/scrape`, filters by rating, computes sentiment, saves to Airtable.
5. Chat replies with a confirmation and a preview card showing the top 3 leads with name, rating, and sentiment badge.
6. User goes to Database, sees all 5 leads in the table.
7. `Reach Out Stage` and `Follow-up` columns show whatever the user has filled in directly in Airtable.
8. User adds a note in the Notes column — syncs to Airtable on blur.