# Chore Management App

A general-purpose chore management Angular app with a Flask backend. The app lets you import a chore list, view it as a weekly checklist, and export it.

## Phase 1: Import → Render → Export (Current)

- **Angular**: Imports `chores.json`, renders the weekly checklist (Daily, This Week, Weekend Chores, On Deck, Inactive)
- **Flask**: Validates chore files, generates PDFs on import (WeasyPrint)
- No CRUD yet, no LLM backend

## Workflow

1. Add/edit chores in `../chores.json` (via Claude Code or manually)
2. Open the Angular app
3. Import the chore file
4. View the weekly checklist
5. Navigate weeks, check off items (in-memory, not persisted)
6. Auto-generated PDF downloads on import
7. Export to save the loaded chore list

## Structure

```
app/
  .claude/        # Epic and story docs (decomposed from constitution.md)
  angular/        # Angular frontend
  api/            # Flask backend (Python)
```

## Running

Angular (todo):
```
cd angular
npm install
ng serve
# Open http://localhost:4200
```

Flask (todo):
```
cd api
pip install -r requirements.txt
python main.py
# Runs on http://localhost:5000
```

## Stories

See `.claude/` for Phase 1, 2, and 3 stories with checklist progress.
