---
name: resume-tailor
description: Tailor a one-page, ATS-friendly LaTeX resume (Jake's template) from personal_info.json to a specific job. Use when the user shares a job posting link or text, or asks to tailor, target, or rewrite their resume for a role.
---

# Resume Tailor

Turns `personal_info.json` and one job posting into a **truthful**, one-page Jake's-template resume, plus a
report on fit and gaps. The model makes every judgment (what to select, how to phrase it, how well it
fits); the bundled scripts do the mechanical parts (fetching, validation, LaTeX rendering, page counting,
literal keyword hits) so those never vary.

- `<skill>` is the folder containing this file. Run scripts with `python` (`python3` on macOS/Linux).
- `<workspace>` is the folder the chat is open in. It holds `personal_info.json` and `output/`.
- **Truthful** is the rule over every step: only choose, reorder, and rephrase what `personal_info.json`
  supports. The full policy is in `references/truthfulness.md`; read it before writing any bullet.

## Inputs

- **Posting**: a URL or pasted text, usually given with the invocation. If neither is given, ask for it.
- **Data**: `<workspace>/personal_info.json`, or a path the user names. If it's missing, tell the user to
  copy `personal_info.example.json` (or follow `<skill>/schemas/personal_info.schema.json`) and stop.

## Steps

### 1. Validate the data

```
python <skill>/scripts/check.py validate <workspace>/personal_info.json --schema personal_info
```

Done when it prints `"valid": true`. Otherwise show the errors and stop. Offer to fix them, and edit the
file only after the user approves the exact change.

### 2. Extract the posting into `job.json`

Read `references/job-extraction.md` and follow it: the fetch helper first, then a browser tool, then
asking the user to paste.

Create the run folder `<workspace>/output/<company>-<role>-<YYYY-MM-DD>/` using lowercase, hyphenated
slugs of at most 40 characters each (for example `northwind-pay-software-engineer-backend-2026-11-07`).
Append `-2`, `-3`, and so on if it already exists.

Done when `<run>/job.json` passes `check.py validate ... --schema job`, and every requirement and keyword
in it comes from the posting.

### 3. Analyze and select

Read `references/selection-rubric.md`. Profile the candidate, map every `required` requirement to its best
evidence in `personal_info.json` (or mark it a gap), score accomplishments and entries, and pick sections,
order, and items within the one-page budget.

Done when every required requirement has an evidence item or a gap with a severity, and you have a ranked
shortlist of entries and bullets.

### 4. Write `tailored_resume.json`

Read `references/bullet-writing.md` and `references/ats-rules.md`. Write `<run>/tailored_resume.json`
(schema `schemas/tailored_resume.schema.json`) as plain text with no LaTeX; `render.py` does all escaping.
Header: name, phone, email, and at most 3 links from `personal_info.json`.

Then run the final audit from `references/truthfulness.md` on every bullet and skill.

Done when it passes `check.py validate ... --schema tailored_resume` **and** every bullet traces to a
source accomplishment with no new numbers, tools, or scope.

### 5. Render and fit to one page

```
python <skill>/scripts/render.py <run>/tailored_resume.json -o <run>/resume.tex
python <skill>/scripts/check.py budget <run>/tailored_resume.json
```

`budget` estimates page fill from the template's real glyph widths. It lists `warnings` (over budget,
headings too wide) and `tighten` (bullets or skills rows that wrap by only 1-3 words).

If `tectonic --version` works, compile and count pages. The first compile downloads LaTeX packages and can
take about a minute; tell the user.

```
tectonic --keep-logs --outdir <run> <run>/resume.tex
python <skill>/scripts/check.py pages <run>/resume.pdf
```

Fix in this order, edit `tailored_resume.json`, and repeat this step after each round of fixes:

- **Too-wide headings** (`budget` warnings, or `overfull` entries from `pages`): they run off the page.
  Shorten them as described under "Heading rows" in `references/bullet-writing.md`.
- **Orphans** (`budget`'s `tighten` list): rewrite each listed bullet or skills row to fit on one line, or
  to clearly fill two.
- **More than 1 page** (or, without Tectonic, `budget` reports over budget): apply the next trim step from
  the rubric's trim order. Stop after 3 trim attempts and report what still overflows.
- **Under-filled** (`budget` estimates 46 lines or fewer): add the next-best item from the rubric.
- Without Tectonic, `resume.tex` is the deliverable. Note in the report that it wasn't compiled.

Always change content in `tailored_resume.json` and re-render. `resume.tex` is generated output: hand
edits get overwritten and can break escaping or the ATS-safe layout.

Done when `pages` reports `"ok": true` (one page, no overfull boxes) and `budget` has no warnings and an
empty `tighten` list. Without Tectonic, the same applies minus `pages`. If 3 trim attempts are used up,
report what still doesn't fit.

### 6. Score and write `report.md`

```
python <skill>/scripts/check.py keywords <run>/job.json <run>/resume.tex
```

For every `missing` or `variant` keyword that `personal_info.json` truthfully supports, first fix the
wording in `tailored_resume.json` (use the posting's exact term in a bullet that demonstrates it), then
rerun step 5 and this command. Only true gaps, and terms that would overstate the source (for example
"owned" when the source says "built"), stay missing.

Then read `references/report-format.md` and write `<run>/report.md`. The fit and keyword scores are your
semantic judgment; the `keywords` output is the literal-match cross-check you report beside them.

Done when no supported keyword is left `missing`, and `report.md` has every section in that format with
every gap and suggested addition listed.

### 7. Present

In the chat, give: the fit verdict and percentage, the 3-5 most important selection decisions, the gaps
by severity, the suggested additions that need confirmation, and links to `resume.tex`, `resume.pdf` (if
compiled), and `report.md`. Then offer to iterate.

## Iterating in the same chat

- **Change requests** ("swap tinykv for DocuChat", "emphasize backend", "shorter skills"): edit
  `tailored_resume.json`, then rerun steps 5-6 in the same run folder and add the change to the report's
  change log. Push back, citing `references/truthfulness.md`, on any request that would add an unsupported
  claim.
- **New facts from the user** ("I did use Terraform there"): propose the exact `personal_info.json` edit as
  a diff (path, old value, new value). Apply it only after an explicit yes, re-run step 1, then regenerate
  from step 3.
- **A different job**: start a new run from step 2.
