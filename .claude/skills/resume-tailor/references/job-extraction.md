# Job extraction: posting to `job.json`

Goal: a faithful, structured `job.json` (schema: `schemas/job.schema.json`) for the posting. Everything
downstream (selection, keyword mirroring, scoring) reads this file, so extraction errors propagate.

## 1. Get the posting text

Pasted text: skip to step 2 with `source.method = "pasted"`, `confidence = "high"`.

URL: run the fetch helper. Do not use a generic web-fetch tool first; those convert pages to markdown and
drop the `<script type="application/ld+json">` block that holds the structured posting.

```
python <skill-dir>/scripts/fetch_posting.py "<url>" -o <run-dir>/raw_posting.json
```

The helper tries, in order:

1. **JSON-LD `JobPosting`** embedded in the page (Lever, Ashby, Workable, SmartRecruiters, most company
   career sites). Gives title, company, location, employment type, and the full description.
2. **Job-board public API** for recognized hosts, used when there's no JSON-LD because it's cleaner than
   scraped text:
   - Greenhouse `boards.greenhouse.io/{board}/jobs/{id}`, `job-boards.greenhouse.io/...`, or `?gh_jid=` with `for=`
     → `boards-api.greenhouse.io/v1/boards/{board}/jobs/{id}`
   - Lever `jobs.lever.co/{company}/{uuid}` → `api.lever.co/v0/postings/{company}/{uuid}`
   - Ashby `jobs.ashbyhq.com/{org}/{uuid}` → `api.ashbyhq.com/posting-api/job-board/{org}`
   - Workday `{tenant}.wdN.myworkdayjobs.com/{site}/job/...` → `/wday/cxs/{tenant}/{site}/job/...`
   - LinkedIn `linkedin.com/jobs/view/{id}` or `?currentJobId=` → `linkedin.com/jobs-guest/jobs/api/jobPosting/{id}`
     (often rate-limited with HTTP 429)
3. **Visible page text** with scripts, styles, nav and footers stripped.

Read the result's `confidence`:

| Confidence | Meaning | Next step |
|------------|---------|-----------|
| `high` | JSON-LD or a board API returned a full description | Use it |
| `medium` | Page text looks like a real posting | Use it; check that it is one posting, not a list, and ignore application-form text, benefits boilerplate, and EEO statements |
| `low` | Fetch failed, page is short, or it reads "enable JavaScript", "sign in", "captcha", "expired" | Go to step 4 |

4. **Browser tool.** If the chat has a browser tool (for example Cursor's built-in browser, or a Playwright
   or Chrome MCP server in Claude Code), open the URL, wait for the posting to render, and copy the visible
   title, company, location, responsibilities, and qualifications. Set `source.method = "browser"`. Don't
   log in, solve captchas, or click "apply". Stop if the page needs any of those.
5. **Ask the user to paste** the posting text. Say which steps failed and why (for example "LinkedIn
   returned 429 and no browser tool is available"). Never guess at a posting you could not read.

Indeed, Glassdoor, and logged-in LinkedIn usually block automated requests. A direct company career
page or the Greenhouse/Lever/Ashby link for the same job usually works, so suggest one if the user has it.

## 2. Structure it into `job.json`

Fill every required field. Copy terms exactly as the posting spells them, because ATS keyword matching is
largely literal ("Node.js" is not "NodeJS").

- `company`, `title`, `location`, `employment_type`: from the structured data when available.
- `seniority`: `intern`, `new-grad`, `junior` (0-2 yrs), `mid` (3-6), `senior` (7+), `staff+`, or `unknown`.
  Use title words (Intern, New Grad, Senior, Staff) and the years requirement.
- `years_experience`: the minimum years asked for, or `null`.
- `domain`: the industry or product area, such as "fintech payments" or "developer tools".
- `company_summary`: one sentence on what the company or team does, taken from the posting.
- `responsibilities`: the top 4-8 duties, condensed.
- `requirements`: every qualification line, each classified:

  | `category` | Meaning | Example |
  |------------|---------|---------|
  | `core-technical` | The stack the role revolves around | "Proficiency in Go or Java" |
  | `supporting-technical` | Infra and tooling around the core | "Familiarity with Docker" |
  | `process` | How work gets done | "CI/CD", "code review", "Agile" |
  | `soft-skill` | Collaboration, communication, leadership | "Clear written communication" |
  | `nice-to-have` | Explicitly optional ("bonus", "nice to have", "preferred") | "Payments experience a plus" |
  | `boilerplate` | Generic filler that matches nothing | "Fast-paced environment", "team player" |

  `required: true` for "must", "required", "you have", or an unqualified list under "Requirements";
  `false` for "preferred", "nice to have", "bonus", or "plus".

- `keywords`: every term an ATS or recruiter would scan for. Use 10-25 terms, not every noun.
  - `priority`: `required` if it appears in a required qualification, `preferred` if only optional, `context`
    for domain and title words that help but are not skills.
  - `category`: `hard-skill`, `soft-skill`, `domain`, or `title`.
  - `aliases`: other spellings that mean the same thing (`["API"]` for "APIs", `["idempotency"]` for
    "idempotent"). `check.py keywords` already knows common ones (JS/JavaScript, k8s/Kubernetes,
    Postgres/PostgreSQL, CI/CD forms, AWS forms).
  - Always include the job title itself (`category: "title"`).
- `description_text`: the cleaned full posting text, for reference during iteration.
- `source`: `url`, `effective_url`, `method`, `confidence`, `attempted`, and `retrieved` (today, YYYY-MM-DD).

Validate before moving on:

```
python <skill-dir>/scripts/check.py validate <run-dir>/job.json --schema job
```
