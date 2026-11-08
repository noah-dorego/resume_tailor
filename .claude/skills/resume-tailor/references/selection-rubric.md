# Selection rubric

How to decide what from `personal_info.json` goes on a one-page resume for a given `job.json`. Score
openly: record the top reasons in the report so the user can disagree.

## 1. Profile the candidate against the role

From `personal_info.json` dates and `job.json`:

- **Career stage**: student or new grad (latest education `end` is in the future or within the last 12
  months, or total full-time experience is under 1 year); junior (0-2 yrs); mid (3-6); senior (7+). Count
  internships, co-ops, and part-time roles as experience, but they don't make someone "senior".
- **Move type**: same track (backend to backend), adjacent (full-stack to backend), or a switch (for
  example IT support to software). For adjacent moves and switches, transferable bullets matter more than
  exact stack matches.
- **Requirement gate**: list `job.json` requirements with `required: true`. For each one, find the best
  supporting evidence in the JSON (an accomplishment, a project, a course, or a skill). Requirements with
  no evidence become gaps (see `truthfulness.md`).

## 2. Score every accomplishment

For each accomplishment of each work experience and project (and each achievement):

| Signal | Points |
|--------|--------|
| Demonstrates a `required` keyword or `core-technical` requirement (via its `text`, `skills`, or clearly the entry's `tech_stack`) | +3 each, max +9 |
| Demonstrates a `preferred` keyword or `supporting-technical` / `process` requirement | +2 each, max +6 |
| Matches a responsibility or the `domain` (for example payments work for a payments company) | +2 |
| Shows a soft-skill requirement with evidence (presented, mentored, led N people) | +1 |
| Has a concrete metric in `text` or `metrics` | +1 |
| Entry ended within the last 12 months or is `present` | +2 (within 24 months: +1) |
| `pin: true` | Always include when its entry is shown |

The matching is semantic: "event-driven reconciliation with Kafka" demonstrates "event streaming
systems". Judge the meaning, not just the string, but stay inside what the text actually shows.

**Entry score** = the sum of its top 3 accomplishment scores + 2 if the role title or project theme is
close to the target title (Software Engineer for SWE, Backend for backend, ML for ML).

## 3. Choose sections and their order

Default `section_order`:

| Candidate | Order |
|-----------|-------|
| Student, new grad, or intern target | `education`, `experience`, `projects`, `skills` |
| Everyone else | `experience`, `projects`, `skills`, `education` |

Then:

- **Projects**: include when the candidate is early-career, when projects cover required keywords that
  experience doesn't, or when they score higher than the weakest experience entry. For a senior
  candidate with strong matching experience, Projects may be dropped entirely.
- **Achievements**: add after `skills` only if space remains *and* at least one achievement scores 2 or
  more (relevant hackathon, competition, certification, publication). It's dropped first when trimming.
- **Interests**: add last only if relevant to the company or role (gaming interest for a game studio, a
  climbing hobby for an outdoor brand, open source for a dev-tools company). Otherwise leave it out.
- No summary or objective section (decided for this skill).

## 4. Fill the page within budget

Starting budget for one page (from calibrating Jake's template):

| Item | Limit |
|------|-------|
| Experience entries | 2-4 (at most 4) |
| Projects | 1-3 |
| Bullets across experience and projects | 10-16 |
| Bullets per role | 2-4 (3-4 for the most recent or most relevant) |
| Bullets per project | 2-3 |
| Technical Skills rows | at most 4 |
| Education detail lines | 0-1 per school |
| `check.py budget` estimate | at most 54 lines (the page overflows at about 57) |

Pick entries in score order until the budget is used, then render them in reverse-chronological order
within each section. Within an entry, order bullets by score, highest first.

Keep at least one entry that shows each *required* keyword you can support. Coverage beats a slightly
higher score elsewhere.

## 5. Trim order when it doesn't fit (more than 1 page, or budget over)

Apply one step at a time, re-render, and re-check:

1. Remove Interests, then Achievements.
2. Tighten the bullets in `check.py budget`'s `tighten` list (they wrap by only 1-3 words) so each fits
   on one line.
3. Remove the lowest-scoring non-pinned bullet from the entry with the most bullets (never take a role
   below 2 bullets or a project below 1).
4. Remove the lowest-scoring project, or the oldest, least relevant role.
5. Remove the education `details` line.
6. Drop the 4th skills row by merging it into the 3rd.

Never shrink fonts, margins, or spacing to make content fit. The template's layout stays as it is.

## 6. Use space that's left over

If the page compiles with clear room to spare (`check.py budget` estimates 46 lines or fewer), add the
next-best item: first a 3rd or 4th bullet for the most relevant role, then another project, then
Achievements. A full page signals more experience than a two-thirds page.
