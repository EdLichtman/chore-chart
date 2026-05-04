# Almanac Document Visual Validation Checklist

Agent: Use this checklist to inspect the generated `chore_almanac.png` images systematically. Report PASS or FAIL for each rule.

---

## Rule 1: Subchores in Details — Bold Bullets, Indented Checkboxes
- **Visual check**: In Details sections, subchores appear as bold bullet points (`• Subchore Name`) under their H4 parent heading. Detail checkboxes (☐) are indented under each subchore.
- **PASS**: Subchore names are bold, bulleted, and visually nested; detail items are indented further with ☐
- **FAIL**: Subchores and details at the same level; no bullet or indentation
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 2: Detail Bullets — Open Square Checkboxes (☐)
- **Visual check**: Each detail item should render as an open checkbox character (☐), not `[ ]` or `-`
- **PASS**: All detail items show ☐ checkbox character
- **FAIL**: Detail items show `[ ]`, dashes, or other characters instead of ☐
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 3: Predicted Dates — Stacked Vertically with Checkboxes
- **Visual check**: Predicted dates in table cells should be stacked vertically (one per line), each preceded by ☐
- **PASS**: Dates appear as:
  ```
  ☐ Apr 01
  ☐ May 01
  ☐ Jun 01
  ```
- **FAIL**: Dates appear horizontally or without ☐ prefix
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 4: Warning — Yellow Background Highlighting
- **Visual check**: Warning blockquotes should have a solid yellow/olive background fill
- **PASS**: Warning text and ⚠ icon appear on a solid yellow background; text is clearly readable
- **FAIL**: Warning appears as regular text without background highlighting
- **Certainty**: HIGH
- **Status**: IMPLEMENTED — verify visually

---

## Rule 5: Section Separators — No Horizontal Lines Between Sections
- **Visual check**: Between section headings (e.g., "Look Ahead to Summer:" and "Spring Details:"), there should be NO horizontal lines
- **PASS**: Only blank space between section headings
- **FAIL**: Horizontal lines appear between sections
- **Certainty**: HIGH
- **Status**: IMPLEMENTED — verify visually

---

## Rule 6: Table Row Count — No Empty Rows
- **Visual check**: Tables should contain only rows with data; no extra empty bordered rows
- **PASS**: Each table row contains at least one data value or is the header row
- **FAIL**: Empty bordered rows with no content appear below data rows
- **Certainty**: HIGH
- **Status**: UNCERTAIN — verify visually

---

## Rule 7: Table Sizing — Full Width, Correct Column Proportions
- **Visual check**: Tables should fill the page width. Column order: Chore | Category | Predicted Dates | Actual
- **PASS**: Tables span the full text area; columns are proportional and content fits without incorrect wrapping
- **FAIL**: Tables too narrow/wide; columns compress; content overflows
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 8: Empty Pages — No Blank Pages
- **Visual check**: No blank pages should exist in the document
- **PASS**: Each page contains content
- **FAIL**: One or more completely blank pages appear between sections
- **Certainty**: HIGH
- **Status**: UNCERTAIN — blank page still appears between Spring and Summer; `remove_empty_pages` runs but has not resolved it

---

## Rule 9: Footer — Season Name Left, Page Number Right
- **Visual check**: Each page should have a footer with the current season name (from STYLEREF Heading 2) on the left and page number on the right
- **PASS**: Footer displays as `Spring (Mar 20 - Jun 20)                    3`
- **FAIL**: No footer; footer missing season or page number; wrong season name shown
- **Certainty**: HIGH
- **Status**: IMPLEMENTED — verify that STYLEREF resolves correctly and doesn't show "Spring Details:" or similar sub-headings

---

## Rule 10: Season Date Validation — Dates Match Section
- **Visual check**: Predicted dates in each seasonal section must fall within that season's date range
- **PASS**: All dates in "Winter" fall Dec 21 – Mar 19; "Spring" Mar 20 – Jun 20; "Summer" Jun 21 – Sep 22; "Fall" Sep 23 – Dec 20
- **FAIL**: Dates appear in wrong season
- **Seasonal boundaries**:
  - Winter: Dec 21 – Mar 19
  - Spring: Mar 20 – Jun 20
  - Summer: Jun 21 – Sep 22
  - Fall: Sep 23 – Dec 20
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 11: As-Needed Chores Page — Exists, After Seasonal Sections
- **Visual check**: An "As-Needed Chores" page should appear after the Fall section and before the Purchase Schedule page
- **PASS**: Page exists with header and table of as-needed tasks with "Last Done" column
- **FAIL**: Page missing or in wrong order
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 12: Purchase Schedule Page — Exists at Document End
- **Visual check**: A "Purchase Schedule" page should appear as the final page of the document
- **PASS**: Final page shows "Purchase Schedule" header and table of items to buy
- **FAIL**: Page missing or appears before As-Needed Chores
- **Certainty**: HIGH
- **Status**: CORRECT ✓

---

## Rule 13: Heading Hierarchy — Season is H2, Nothing Else
- **Visual check**: Only the season name headings (e.g., "Spring (Mar 20 - Jun 20)") should render as H2. "Look Ahead", "Details", and chore names should be H3/H4 and visually smaller/subordinate.
- **PASS**: Season name is the largest heading per section; Details heading and Look Ahead heading are visually smaller
- **FAIL**: "Spring Details:" appears at the same visual weight as "Spring (Mar 20 - Jun 20)"
- **Certainty**: HIGH
- **Status**: CORRECT ✓ — Details heading demoted to H3; STYLEREF footer should now show season name only

---

## Validation Report Template

When inspection is complete, generate a report:

```
VALIDATION REPORT — chore_almanac.png
Generated: [DATE]

✓ PASS: Rule 1  — Subchore bullets indented with ☐ items below
✓ PASS: Rule 2  — Detail bullets are ☐ checkboxes
✓ PASS: Rule 3  — Predicted dates stacked vertically with ☐
? CHECK: Rule 4  — Warning yellow background (verify visually)
? CHECK: Rule 5  — No section separator lines (verify visually)
? CHECK: Rule 6  — No empty table rows (verify visually)
✓ PASS: Rule 7  — Table sizing correct
? CHECK: Rule 8  — No blank pages (known issue between Spring/Summer)
? CHECK: Rule 9  — Footer shows season name + page number
✓ PASS: Rule 10 — All dates match their seasons
✓ PASS: Rule 11 — As-Needed Chores page present
✓ PASS: Rule 12 — Purchase Schedule page at end
✓ PASS: Rule 13 — H2 is season only; sub-headings correctly subordinate
```
