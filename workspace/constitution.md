# Chore Checklist — Constitution
> The rules that govern how chores are defined, stored, displayed, and refreshed.

---

## Core Chore Rules

- [ ] **Rule 1 — Interval Required:** Every chore must repeat on a fixed interval of `n` units of time (e.g., every 1 week, every 2 weeks, every 1 month).

- [ ] **Rule 2 — Valid Intervals:** A chore's interval is expressed as `n` + `unit`, where:
  - `unit` is one of: `day`, `week`, `month`, `year`
  - `n` is a positive integer
  - Named aliases (e.g., "bi-weekly", "quarterly") are display labels only — the underlying data is always `n` + `unit`

- [ ] **Rule 3 — Daily Chores Render as 7 Checkboxes:** A chore with interval `n:1, unit:day` renders as 7 individual checkboxes (one per day: S M T W T F S) instead of a single checkbox.

- [ ] **Rule 9 — Weekend and Daily Are Mutually Exclusive:** A chore flagged as a weekend chore cannot have interval `n:1, unit:day`. These properties cannot coexist.

- [ ] **Rule 10 — Non-Weekend Chores Have No Default Day:** A chore not flagged as a weekend chore may be completed on any day of the week. No day is implied or enforced.

- [ ] **Rule 11 — Day Designation for Configurable Chores:** A chore marked `dayConfigurable: true` includes a `day: ____` blank on the printed checklist, allowing the user to assign a specific day at the start of the week. When a chore is added, ask: *"Is this something you assign to a specific day of the week?"* Default to `true` for weekly chores, but allow override for any interval.

- [ ] **Rule 19 — Monthly Day Pinning:** A chore with `unit:month` (any `n`) always has a pinned day of month. When the chore is added, ask: *"Would you like this at the beginning or middle of the month?"* The answer maps to either the **1st** or the **15th**. This is stored on the chore file and shown on the checklist.

- [ ] **Rule 20 — Natural Language Interval Input:** When a user describes a chore's frequency in natural language (e.g., "every month and a half", "every other month", "twice a month"), the system converts it to the nearest clean `n` + `unit` representation and confirms: *"I'll set that as [interval] — does that sound right?"*

- [ ] **Rule 22 — Location Splitting:** If a chore references multiple locations (e.g., "first and second floor bathrooms"), split it into separate chore files automatically. If only one location is mentioned, ask: *"Would you like a separate chore for [counterpart location]?"*

- [ ] **Rule 23 — Week Pin (Odd/Even):** A chore with `n:2, unit:week` may have an optional week pin of `odd` or `even`, based on the ISO week number of the year. When two chores are created as location-split counterparts with the same bi-weekly interval, the system automatically assigns one `odd` and one `even` and confirms with the user. The checklist for a given week only shows the chore whose week pin matches the current ISO week number.

---

## Weekend Chores

- [ ] **Rule 8 — Weekend Flag:** Each chore has an optional weekend flag. When a new chore is added, the system asks: *"Is this typically a weekend chore?"*
  - If yes: the chore is marked `(weekend)` on the checklist and visually demarcated within its frequency section.
  - Weekend chores remain within their frequency bucket — they are not moved to a separate section.

---

## Chore Files

- [ ] **Rule 21 — Chore Names Are Verbatim:** The chore name is taken exactly as the user states it, preserving verbs and descriptors (e.g., "Refill Cat Food", not "Cat Food"). Do not paraphrase or shorten.

- [ ] **Rule 15 — Chore Data Structure:** Each chore is stored as an entry in `chores.json` and contains:
  - `id` — unique identifier (kebab-case)
  - `name` — verbatim chore name (Rule 21)
  - `interval` — `n` + `unit` (Rule 2)
  - `weekend` — `true` / `false` (Rule 8)
  - `dayConfigurable` — `true` / `false`; whether the user assigns a specific day at the start of the week (Rule 11)
  - `dayPin` — **required** for `unit:month` chores (1 or 15); `null` for all others (Rule 19)
  - `weekPin` — **required** for `n:2, unit:week` location-split pairs (`"odd"` or `"even"`); `null` for all others (Rule 23)
  - `lastAligned` — ISO date string or `"pending"` if not yet aligned (Rule 5)
  - `notes` — array of strings; vital information displayed on the checklist alongside the chore
  - `synchronizedWith` — array of chore IDs; empty array if none (Rule 25)
  - `requirements` — array of sub-tasks with their own `id`, `name`, `interval`, and `lastAligned` (Rule 26)
  - `annualCadence` — array of cadence entries with `startDate` (MM-DD) and `interval` or `status: "inactive"` (Rule 12)

---

## Annual Cadence

> Annual cadence is when a chore's interval changes at a specific time of year — for example, mowing goes weekly in May, bi-weekly in August, and inactive in November. If a chore always stays the same frequency year-round, it has no annual cadence.

- [ ] **Rule 12 — Annual Cadence Overrides:** Each chore may define cadence entries that override its default interval starting on a specific month and day (e.g., May 1, August 15). A chore may also be set to `inactive` for a date range, removing it from the checklist entirely during that period. Cadence entries are month-anchored, not season-anchored.

- [ ] **Rule 13 — Annual Cadence Flow:** After the alignment flow, the system asks: *"Would you like to review your annual cadence?"*
  If yes, the system reviews each chore's cadence entries and prompts re-alignment where applicable.

- [ ] **Rule 14 — Re-alignment Start Date:** Each cadence entry has a single date field that serves as both the interval start date and the re-alignment prompt trigger. The system begins prompting for cadence re-alignment on that date. Once re-aligned, it does not prompt again until the next cadence entry's date.

---

## Refresh & Alignment Workflow

- [ ] **Rule 16 — Date Capture (Once Per Session):** At the very start of a refresh, the system captures today's date and day of the week exactly once. This value is reused for all subsequent calculations — week anchoring, alignment due dates, cadence re-alignment checks — without asking again.

- [ ] **Rule 4 — Week Anchoring with Confirmation:** When the user initiates a refresh, calculate the anchor Sunday using the Wednesday/Thursday boundary, then confirm:
  - **Sunday–Wednesday:** *"The week started on Sunday [date]. Are you planning chores for this past week, or planning ahead for next week?"*
  - **Thursday–Saturday:** *"The next week starts on Sunday [date]. Are you planning for this upcoming week, or for the previous week?"*
  - The user's answer sets the active week window for all subsequent steps.

- [ ] **Rule 5 — Alignment Period:** Each chore has a stored **last-aligned date**. The **next due date** is calculated as: `last-aligned date + interval`. Daily chores (`n:1, unit:day`) are exempt — they render fresh each week as 7 checkboxes and do not require alignment tracking. Their `lastAligned` is always `null`. Weekly chores that show every week regardless also do not require `lastAligned`. When adding any chore with interval `n:2, unit:week` or longer, always ask: *"Do we need a last-aligned date for this, or does it show every week regardless?"*

- [ ] **Rule 6 — Refresh Workflow Order:** When the user says *"let's refresh the chores"*:
  1. Ask: *"Would you like to align any periodic chores first?"*
  2. If yes — run the alignment flow:
     - **Step 1 (Upcoming):** Present chores whose next due date falls within the active week window:
       *"Based on my previous alignment, the following chores are coming up this week: [chore] — last aligned [date], every [interval]. Does this sound correct?"*
     - **Step 2 (Overdue):** Present chores where `last-aligned date + interval` is earlier than today:
       *"Moving onto the remaining alignments, the following haven't been re-assigned yet. Are these assignments correct?"*
     - **Step 3 (Early completion):** Ask: *"Is there any chore that needs re-alignment from being done early?"* If yes, present any chore whose next due date is more than 2 weeks away as a candidate for manual re-alignment. (Rule 18)
  3. After alignment, ask: *"Would you like to review your annual cadence?"* (Rule 13)
  4. Generate and print the checklist (see Rule 17).

- [ ] **Rule 27 — Overdue & This Week Placement:** Any chore that is overdue (past due date) or due within the active week window must appear in "This Week" (or "Weekend Chores" if due on a weekend). Such chores are never placed in "On Deck" or future sections, regardless of their interval length. **Multi-week view:** In 4-week view, a past-due or in-grace chore appears ONLY in the current week (Week 1), never in future weeks (Weeks 2–4). A chore appears exactly once per due cycle, in the week containing its actual due date.

- [ ] **Rule 17 — Checklist Rendering:** The printed checklist is structured as follows:
  - Header: `Week of: [Sunday date]`
  - **Daily** — table with columns for each day of the week (S M T W T F S) and one row per daily chore
  - **This Week** — non-weekend chores due within the active week window, grouped by frequency (e.g., "Weekly", "Every 2 Weeks", "Monthly"):
    - Chores with `dayConfigurable: true` include a `day: ____` blank
    - Notes render as indented bullet points beneath the chore
    - Requirements render as indented checkboxes beneath the parent chore, only when due
  - **Weekend Chores** — weekend chores due within the active week window, grouped by frequency
    - No day blanks (completed any time over the weekend)
    - Notes and requirements render the same way as "This Week"
  - **On Deck** — chores due in the coming 1–2 weeks AFTER this week (not due this week, not overdue), reference only (no checkboxes) (Rule 27)
  - **Off Rotation** — chores due beyond the "on deck" window, reference only (no checkboxes)
  - **Inactive** — chores suppressed by annual cadence, reference only (no checkboxes)

- [ ] **Rule 7 — Alignment Storage:** Last-aligned dates and cadence re-alignment dates are persisted in memory between sessions and survive a fresh checklist print.

- [ ] **Rule 25 — Synchronized Chores:** Chores marked as synchronized share the same interval and last-aligned date. When one is aligned, the other updates automatically. They always appear together on the checklist.

- [ ] **Rule 24 — Grace Window (Early or Late Completion):** When a chore is completed early or late, find the nearest due date and check if the completion falls within the grace window of that date:
  - `unit:day` or `unit:week` → grace window is **1 week** (7 days)
  - `unit:month` → grace window is **1 week** (7 days)
  - `unit:year` → grace window is **2 weeks** (14 days)
  - **Within grace window:** next due date = `nearest due date + interval` (no drift)
  - **Outside grace window:** next due date = `actual completion date + interval` (intentional reset)
  - Calculation: `|actual completion date − nearest due date| ≤ grace window`
  - **Overdue badge:** A chore is only marked as "overdue" if today is OUTSIDE the grace window of its due date. If today is within the grace window, the chore is not overdue (it is "in progress" for that due cycle).
