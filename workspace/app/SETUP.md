# Phase 1 Setup Guide

## Angular Frontend

### Prerequisites
- Node.js 18+ (check: `node --version`)
- npm (check: `npm --version`)

### Installation

```bash
cd app/angular
npm install
```

### Running

```bash
npm start
```

This will:
1. Start the Angular development server on `http://localhost:4200`
2. Auto-open in your browser

The app will:
- Show a file import area
- Allow you to drag-drop or select a `chores.json` file
- Render the weekly checklist
- Let you navigate weeks, check items, and export

### Building for Production

```bash
npm run build
```

Output goes to `app/angular/dist/chore-app/`

---

## Flask Backend

### Prerequisites
- Python 3.9+ (check: `python --version`)
- pip (check: `pip --version`)

### Installation

```bash
cd app/api
pip install -r requirements.txt
```

### Running

```bash
python main.py
```

This will start the Flask development server on `http://localhost:5000`

**Endpoints:**
- `GET /health` — Health check
- `POST /chores/validate` — Validate a chore file
- `POST /chores/import` — Import a file and generate PDF

### Testing the API

```bash
# Test health
curl http://localhost:5000/health

# Test import (generates PDF)
curl -X POST http://localhost:5000/chores/import \
  -H "Content-Type: application/json" \
  -d @../chores.json \
  --output checklist.pdf
```

---

## Workflow

1. **Add/edit chores** in `../chores.json` (via Claude Code or manually)
2. **Open Angular app** (`http://localhost:4200`)
3. **Import the chore file** — app validates and loads it
4. **View the checklist** — renders weekly view with all sections
5. **Navigate weeks** — use Prev/Next buttons
6. **Check items** — in-memory only (not persisted)
7. **Print or Export** — download as file or print to paper
8. **PDF generation** — auto-generated on import (via Flask)

---

## Notes

- **Flask CORS:** Enabled for localhost, safe for development
- **PDF Generation:** Uses WeasyPrint (pure Python, no external dependencies)
- **In-Memory State:** Angular stores chore state in memory; no persistence until export
- **Print CSS:** Optimized for paper and PDF output
- **Bootstrap:** Used for accessible, printable checkboxes

---

## Troubleshooting

**Angular won't start:**
- Delete `node_modules/` and run `npm install` again
- Check that port 4200 is available

**Flask PDF generation fails:**
- Ensure WeasyPrint is installed: `pip install WeasyPrint`
- On macOS/Linux, you may need additional system dependencies (see WeasyPrint docs)

**CORS errors:**
- Make sure Flask is running on `http://localhost:5000`
- Angular is configured to hit this URL; check `environment.ts`

---

## Next: Phase 2

When ready to add in-app CRUD:
- Add chore management forms
- Implement alignment workflow
- Add real persistence to in-memory state
- Wire up `/chores/get` and `/chores/update` Flask endpoints
