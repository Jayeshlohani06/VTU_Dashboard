# VTU Student Performance Dashboard

A Dash + Flask web app for analyzing VTU student result data with interactive pages, exports, and lightweight API endpoints.

## Features

- Multi-page dashboard: Overview, Ranking, Subject Analysis, Student Detail, Branch Analysis, Branch Intelligence
- KPI and performance insights from uploaded result files
- Feedback capture integration via Google Sheets
- PDF export support
- Built-in API endpoints for health and session-based summaries
- Light/dark theme support with custom CSS assets

## Tech Stack

- Python 3.11
- Dash, Flask, Plotly, Pandas, NumPy
- Flask-Caching
- Waitress (Windows production entry via `wsgi.py`)
- Gunicorn (container production entry)

## Project Structure

- `app.py`: Main Dash application and route/callback wiring
- `wsgi.py`: WSGI entrypoint for production serving
- `api.py`: `/api/*` endpoints
- `pages/`: Page-level layouts and callbacks
- `services/`: Integration and business services (PDF, Google Sheets, etc.)
- `utils/`: Analytics and data loading utilities
- `assets/`, `styles/`: Frontend CSS/JS resources
- `tests/`: Pytest test suite

## Quick Start (Local)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

- Copy `.env.example` to `.env`
- Update values as needed (especially `SECRET_KEY` and Google credentials)

4. Run in development mode:

```bash
python app.py
```

Default app host/port come from environment variables (`HOST`, `PORT`).

## Production Run (Windows)

Use Waitress via the provided WSGI entrypoint:

```bash
python wsgi.py
```

This starts the app on `0.0.0.0:8080` as configured in `wsgi.py`.

## Docker Run

Build and run with Docker Compose:

```bash
docker compose up --build
```

Container health endpoint:

- `http://localhost:8080/api/health`

## API Endpoints

- `GET /api/health`
- `GET /api/metrics`
- `GET /api/summary?session_id=...`
- `GET /api/subjects?session_id=...`
- `GET /api/student/<student_id>?session_id=...`

## Testing

Run tests with:

```bash
python -m pytest tests/ -v
```

## Environment Variables

See `.env.example` for full list. Important values:

- `HOST`, `PORT`, `DEBUG`
- `LOG_LEVEL`
- `CACHE_TYPE`, `CACHE_DEFAULT_TIMEOUT`, `CACHE_THRESHOLD`
- `SECRET_KEY`, `MAX_UPLOAD_SIZE_MB`, `RATE_LIMIT_FEEDBACK`
- `GOOGLE_SHEET_URL`, `GOOGLE_CREDENTIALS`
- `ENABLE_FEEDBACK`, `ENABLE_TOUR`

## Notes

- Keep `service_account.json` out of version control (already ignored).
- Place custom CSS/JS files under `assets/` and page CSS under `styles/`.
