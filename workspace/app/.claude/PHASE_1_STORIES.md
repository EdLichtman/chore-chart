# Phase 1: Import → Render → Export

**Goal:** Replace the PowerShell HTML generator with an Angular app. The workflow is: user adds/edits chores in `chores.json` (via Claude Code) → imports into Angular → views weekly checklist → exports + PDF generation.

**Backend (Phase 1):** Flask handles PDF generation only (`POST /chores/import`).

---

## User Stories

### 1.1 — Import a chores.json file, load into app memory

- [ ] **Angular:** File input (drag-drop or file picker)
- [ ] **Angular:** Validate schema against JSON Schema
- [ ] **Angular:** Load chore data into in-memory state
- [ ] **Angular:** Show success message with chore count

**Acceptance Criteria:**
- User can drag-drop or pick a `.json` file
- App validates the file has required fields (id, name, interval, etc.)
- Invalid files show a clear error message
- Valid files load and trigger the checklist render

---

### 1.2 — Render weekly checklist: Daily, This Week, Weekend, On Deck, Inactive

- [ ] **Angular:** Calculate week anchor (Sunday) from today
- [ ] **Angular:** Render Daily table (7 checkboxes for S-Sun through Sat)
- [ ] **Angular:** Render This Week section (non-weekend chores due this week)
- [ ] **Angular:** Render Weekend Chores section
- [ ] **Angular:** Render On Deck section (1–2 weeks out, reference only)
- [ ] **Angular:** Render Inactive section (suppressed by cadence)

**Acceptance Criteria:**
- Daily chores show a 7-column table
- Chores appear in correct sections based on interval + weekPin + cadence
- Off Rotation section omitted if no chores qualify

---

### 1.3 — Navigate between weeks (prev/next)

- [ ] **Angular:** Prev/Next week buttons
- [ ] **Angular:** Display current week (Sunday date + ISO week number)
- [ ] **Angular:** Recalculate all sections on week change

**Acceptance Criteria:**
- Buttons update the active week window
- Clicking prev/next re-renders sections with correct chores for that week

---

### 1.4 — Interactive checkboxes (in-memory, accessible & printable)

- [ ] **Angular:** Use Bootstrap (or similar) form-check for accessible checkboxes
- [ ] **Angular:** Checkboxes are checked/unchecked but don't persist (in-memory only)
- [ ] **Angular:** Ensure checkboxes render clearly when printed or exported to PDF

**Acceptance Criteria:**
- Checkboxes are properly labeled (ARIA labels, semantic HTML)
- User can click checkboxes; state persists during the session
- No persistence to file or server (this is a printed checklist)
- Checkboxes print/PDF cleanly (visible boxes, not just form controls)

---

### 1.5 — Overdue indicators

- [ ] **Angular:** Calculate next due date for each chore (lastAligned + interval)
- [ ] **Angular:** Flag chores where due date < today
- [ ] **Angular:** Display visual indicator (e.g., red text, ⚠️ icon) on overdue chores

**Acceptance Criteria:**
- Chores past their due date are visually distinct
- Indicator is clear and persistent as user navigates weeks

---

### 1.6 — Export: download the loaded chore list as a file

- [ ] **Angular:** Add Export button
- [ ] **Angular:** Serialize in-memory chore state to JSON
- [ ] **Angular:** Trigger browser download of the JSON file

**Acceptance Criteria:**
- Clicking Export downloads a valid JSON file
- Downloaded file can be re-imported successfully

---

### 1.7 — On import: auto-generate and download a PDF via Flask

- [ ] **Flask:** Endpoint `POST /chores/import`
- [ ] **Flask:** Receive chore file, validate schema
- [ ] **Flask:** Render chore data as HTML (matching current checklist layout)
- [ ] **Flask:** Convert HTML to PDF (WeasyPrint)
- [ ] **Flask:** Return PDF as downloadable attachment
- [ ] **Angular:** On import, send chore file to Flask and trigger PDF download

**Acceptance Criteria:**
- User imports a file → Flask generates PDF automatically
- PDF matches the layout of the weekly checklist (Daily, This Week, Weekend, On Deck, Inactive)
- PDF downloads when import completes

---

### 1.8 — Smart PDF pagination: if overflow → On Deck + Inactive on page 2

- [ ] **Flask:** Estimate total content height (item count + margins)
- [ ] **Flask:** If Daily + This Week + Weekend would overflow one page, add CSS `page-break-before` before On Deck
- [ ] **Flask:** Render On Deck and Inactive on page 2

**Acceptance Criteria:**
- Single-page output if content fits
- Two-page output if needed; break at a logical place (before On Deck)
- No content split mid-section

---

### 1.9 — Browser print with print CSS

- [ ] **Angular:** Include print CSS (hide buttons, optimize for paper)
- [ ] **Angular:** User can press Ctrl+P and print the checklist

**Acceptance Criteria:**
- Print view is clean and readable
- All sections fit well on printed pages (similar to PDF)

---

## Development Order

1. **1.1 + 1.2** — Import and render the checklist (core MVP)
2. **1.3 + 1.4** — Week nav and checkboxes
3. **1.5** — Overdue indicators
4. **1.6** — Export
5. **1.7 + 1.8** — Flask PDF generation + smart pagination
6. **1.9** — Print CSS

---

## Technical Notes

- **Angular state:** In-memory chore list + current week
- **Flask:** Stateless; receives chore data in request body
- **PDF library:** WeasyPrint (pure Python, no external binary)
- **JSON Schema:** Reference in `../chores.json`
