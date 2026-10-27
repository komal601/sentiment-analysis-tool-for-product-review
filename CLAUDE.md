# CLAUDE.md — Operational Rules for Coding Agents

Cross-Platform E-Commerce Sentiment Analysis & Review Authenticity Tool (Amazon.in vs. Flipkart).
**Read `SPEC.md` before any task.** It defines the features, directory layout, the `/api/v1/analyze` data contract, and the scraping fallback architecture.

---

## Tech Stack Commands

### Backend (`/backend`, Python 3.11+, FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash  (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
playwright install chromium          # one-time browser install
uvicorn app.main:app --reload        # dev server → http://127.0.0.1:8000  (docs at /docs)
pytest                               # full test suite
pytest tests/test_trust.py -v        # single module
FORCE_FALLBACK=1 uvicorn app.main:app --reload   # demo mode: never scrape live
```

### Frontend (`/frontend`, Next.js App Router, TypeScript, Tailwind, Recharts, Lucide)
```bash
cd frontend
npm install
npm run dev                          # dev server → http://localhost:3000
npm run build && npm run lint        # pre-commit check
```

---

## Agent Guardrails

1. **No live scraping loops.** Never run live Playwright scraping in an automated loop against Amazon or Flipkart URLs (this risks IP bans and wastes tokens). Always test scraper logic against local HTML snapshot files in `/backend/app/scraper/snapshots/` first. A single manual live check is allowed only when the user explicitly asks for one. Never attempt to solve or bypass a CAPTCHA. On detection, abort and fall back (SPEC §D).

2. **The API contract is frozen without a SPEC change.** Never modify the JSON response structure of `/api/v1/analyze` without updating `SPEC.md` first, because the Next.js frontend relies strictly on this contract. Any change must update all three together: `SPEC.md` §C, `backend/app/schemas.py`, and `frontend/lib/types.ts`.

3. **Small, modular, tested.** Keep functions modular and under 80 lines. Write unit tests in `/backend/tests/` for every NLP and scoring module (Hinglish normalizer, sentiment, ABSA, trust, fulfillment, drift, summarizer) before wiring it to FastAPI. Tests must not hit the network. Use snapshots, `seed_reviews.json`, or inline fixtures.

4. **Preserve negations and emojis.** During text preprocessing, never strip negation words (`not`, `never`, `no`, plus Hinglish `nahi`, `mat`, `na`) or emojis. They carry polarity ("not good", "👎", "😍"). Don't drop them as stopwords, and don't remove them in unicode/punctuation cleanup.

---

## Additional Conventions

- The 8-second timeout + `seed_reviews.json` fallback in `scraper/fetcher.py` is mandatory. Never remove it or raise the timeout above 8 s.
- Don't commit secrets. LLM API keys go in `backend/.env` (gitignored). The summarizer must have a deterministic fallback for when no key is set.
- `backend/app/data/cache.sqlite` and `.venv/` are gitignored. `seed_reviews.json` and `scraper/snapshots/*.html` are committed.
