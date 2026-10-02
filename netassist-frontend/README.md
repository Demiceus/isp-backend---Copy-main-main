# NetAssist AI — Frontend

Plain HTML/CSS/JS. No framework, no build step. Connects to your existing
Flask + PostgreSQL API — it does not include or replace any backend.

## Files
- `index.html` — local login gate (no auth endpoint was given, so this just starts a session in the browser)
- `dashboard.html`, `chat.html`, `escalations.html`, `reviews.html`, `batch.html`, `admin-ai.html` — one page per feature
- `css/style.css` — shared styling
- `js/api.js` — every backend call, in one place, pointed at `API_BASE_URL`
- `js/app.js` — shared helpers (session check, sidebar highlighting, toasts)

## Running it
1. Start your Flask backend as usual (`http://127.0.0.1:5000`).
2. Serve this folder with any static server — opening the files directly as
   `file://` will break `fetch()` in most browsers. From this folder:
   ```
   python -m http.server 5500
   ```
   then open `http://127.0.0.1:5500`.
3. **Enable CORS on the Flask side** so the browser allows requests from
   `http://127.0.0.1:5500` to `http://127.0.0.1:5000` — e.g. `flask-cors`:
   ```python
   from flask_cors import CORS
   CORS(app)
   ```
   Without this, every request will fail with a network/CORS error even
   though the backend is running.
4. Log in with any name/password, then try Customer Chat with an account
   number like `FRONTEND-TEST-001`.

## Notes on defensive coding
A few backend response shapes weren't fully specified, so the frontend reads
several possible field names and falls back to showing the raw response
rather than guessing (see `escalations.html`, `batch.html`, `admin-ai.html`).
If a field looks wrong once you're pointed at the real API, that's the place
to adjust — everything routes through `js/api.js`.

Two things called for in the spec don't have a matching endpoint yet, so they're
visibly scoped down rather than faked:
- **Complaint category statistics** on the dashboard — `/api/admin/stats` doesn't
  return a per-category breakdown.
- **Recent reviews feed** — there's a POST to submit a review but no GET to list
  them, so the dashboard only shows sentiment totals, and the Reviews page shows
  what you've submitted in the current browser session.
