# Bullet writing

Every bullet on the resume is a rephrasing of an accomplishment in `personal_info.json`. Read
`truthfulness.md` first; these rules only govern *how* to phrase what is already supported.

## The XYZ formula

> Accomplished **[X]** as measured by **[Y]**, by doing **[Z]**.

- **X**: what you did (strong verb + object)
- **Y**: the measurable result. Take it only from the accomplishment's `text` or `metrics`, never estimate.
- **Z**: how you did it (method, tools). This is where supported keywords go.

Order can vary: leading with the result is fine, and identical sentence shapes for every bullet read as
robotic. When there is no metric, give scope or outcome in words ("used by 40 partner schools", "replacing
a nightly batch job") instead of inventing a number.

| From `personal_info.json` | Tailored bullet |
|---------------------------|-----------------|
| text: "Wrote gRPC load tests and tuned PostgreSQL indexes for the merchant balance endpoint"; metrics: ["p95 latency reduced from 420ms to 90ms"] | "Reduced p95 latency of the merchant balance gRPC endpoint from 420ms to 90ms with load tests and PostgreSQL index tuning" |
| text: "Moved image uploads to S3 presigned URLs with a Lambda thumbnail generator, removing upload timeouts"; metrics: ["upload failure rate dropped from 6% to under 0.5%"] | "Cut image upload failures from 6% to under 0.5% by moving uploads to S3 presigned URLs with a Lambda thumbnail generator" |
| "Led weekly tutorials for 35 students on trees, graphs, and hashing in Java" | Keep as is: already specific, verb-first, and one line |

## Hard rules

1. **Length**: aim for one rendered line, roughly **105 characters or less** (a line holds about
   105-115 characters depending on letter widths). Two lines is the hard maximum. A bullet that wraps by
   only 1-3 words wastes a line and looks careless. `check.py budget` measures real glyph widths and lists
   those bullets under `tighten`; rewrite each one to fit on one line, or to clearly fill two.
2. **Start with a strong past-tense action verb** (present tense only for a role that is `present`).
   Good: Built, Designed, Shipped, Reduced, Cut, Automated, Migrated, Implemented, Led, Optimized, Scaled,
   Integrated, Deployed, Instrumented, Refactored, Mentored.
   Avoid: Responsible for, Worked on, Helped with, Assisted, Participated in, Utilized.
3. **No first person** (I, my, we), no trailing period.
4. **One claim per bullet.** Combine two related accomplishments only if both are supported and the result
   still fits in two lines.
5. **Bullet counts**: 2-4 bullets per experience role (most recent and most relevant roles get 3-4,
   older or less relevant roles get 2), 2-3 per project. `pin: true` accomplishments are always included
   when their entry is shown.
6. **Vary verbs**: don't repeat a lead verb within one role, or more than twice on the page.

## Keyword mirroring

- Use the posting's exact spelling for a skill the bullet already demonstrates: JSON "REST endpoints" with
  posting "RESTful APIs" → "RESTful APIs"; JSON "Postgres" with posting "PostgreSQL" → "PostgreSQL".
- Add a tool to a bullet only if the JSON shows it was used in *that* accomplishment: its `text`, its
  `skills`, or the entry's `tech_stack` when the accomplishment clearly involves it.
- Spread keywords out: at most 2-3 technologies per bullet. Don't put the same keyword in every bullet.
- Keep a distinctive, memorable bullet even if it matches nothing in the posting, as long as there's
  space; it shows range.

## Skills rows (Technical Skills section)

Merge `technical_skills` into **at most 4 rows**, in this order:

| Row label | From `technical_skills` |
|-----------|-------------------------|
| Languages | `languages` |
| Frameworks & Libraries | `frameworks` |
| Cloud, DevOps & Databases | `infra` + `dbms` |
| Tools & Platforms | `ai_tools` + `os` + `others` (and any extra categories) |

- Within a row, order skills by relevance: posting keywords first (required before preferred), then
  related skills, then the rest.
- Drop skills that are clearly irrelevant to the role (for example Figma for a backend role), so each row
  stays at one line where possible (about 100 characters including the label).
- Use the posting's spelling for a skill you have (`Node.js`, `PostgreSQL`, `Amazon Web Services (AWS)` if
  the posting spells it out).
- A tool that only appears inside an accomplishment (not in `technical_skills`) may be listed, since it's
  supported, but **never list a skill that appears nowhere in `personal_info.json`**.
- If a row would be empty or trivial, merge it into a neighbor or rename it (for example
  "Databases & Cloud"). Labels stay plain and standard.

## Heading rows

Heading rows (title and dates, company and location, project name with stack, link, and dates) are table
cells: they **can't wrap**, and anything too long runs off the right edge of the page. `check.py budget`
warns about them, and `check.py pages` reports `overfull` boxes after a compile. To fix one:

- Projects: list 3-4 of the most relevant technologies in `tech_stack` (not the whole stack), and drop the
  `link` or give it a shorter `display`.
- Teams: drop `team` if the company line is long; it's optional.
- Never shorten an official title or company name to fit. Shorten what's optional around it.

## Education lines

- `degree` line: "Bachelor of Science in Computer Science, Minor in Statistics", taken from `degree` +
  `minor`.
- `details` (optional, 0-1 lines): GPA if 3.5 or higher (or if the posting asks for it), plus 3-6
  relevant courses chosen for this posting, and honors if short. For example "GPA: 3.8/4.0; Relevant
  Coursework: Distributed Systems, Databases".

## Final self-check per bullet

- Could you defend every word in an interview using only what's in `personal_info.json`?
- Does it start with a verb, fit on one line (or clearly fill two), and avoid filler?
- Is the posting's exact keyword used where it's truthful?
