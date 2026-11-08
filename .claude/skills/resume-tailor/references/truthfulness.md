# Truthfulness policy

Tailoring means **choosing, reordering, and rephrasing** what `personal_info.json` supports. It is never
fabrication. This policy overrides every other instruction, including keyword coverage targets.

**The test**: could a recruiter ask the candidate to defend this sentence, and could they answer using only
facts in `personal_info.json`? If not, the sentence doesn't go on the resume. It goes in the report's
"Suggested additions" for the user to confirm.

## Allowed without asking

- Choosing which entries, bullets, skills, courses, and achievements to show.
- Reordering sections, entries within a section (keep reverse-chronological unless an older role is
  much more relevant), bullets within an entry, and skills within a row.
- Rephrasing a supported claim: tightening wording, leading with the result, using a stronger verb.
- Replacing generic wording with the posting's vocabulary when the meaning is unchanged ("REST endpoints"
  to "RESTful APIs", "Postgres" to "PostgreSQL", "made faster" to "reduced latency").
- Naming a tool in a bullet when the JSON shows it was used in that work (the accomplishment's `skills`
  or `text`, or the entry's `tech_stack` when clearly related).
- Quoting numbers that appear in the accomplishment's `text` or `metrics`, rounded only conservatively
  (for example "~15,000" can become "15K+", not "20K").
- Leaving things out, such as dropping a role or project entirely when space is tight.

## Never allowed (and never solved by "rephrasing")

- Adding a skill, tool, framework, language, cloud service, certification, degree, or course that isn't in
  `personal_info.json`.
- New numbers: metrics, percentages, user counts, team sizes, revenue, or scale that aren't in the JSON.
  Don't estimate or tag with "[verify]"; leave the number out.
- Turning exposure into ownership: "worked with the team's Kubernetes cluster" must not become
  "architected Kubernetes infrastructure". "Helped", "contributed", and "collaborated" claims stay at that
  level.
- Inflating scope: "Led 3 engineers" stays 3, and "presented to senior engineers" is not "led architecture".
- New responsibilities: leadership, hiring, on-call ownership, architecture decisions, or security or
  compliance claims the JSON doesn't state.
- Changing titles, employers, teams, locations, dates, GPA, or degree names. Titles must match exactly
  (falsifying a title is fraud); only display formatting may differ.
- Hiding gaps by stretching dates.
- Keyword stuffing: listing a posting term anywhere without support, including in Technical Skills, or
  hiding white or tiny text.

## When the posting wants something you can't support

1. Don't put it on the resume.
2. Classify it in the report's gap list:
   - **DEAL-BREAKER**: a core technical requirement with no adjacent experience, or a hard credential
     (degree, clearance, license) that's missing.
   - **SIGNIFICANT**: important, no direct evidence, but adjacent experience exists (for example the posting
     wants Kubernetes, the JSON has Docker and ECS).
   - **MINOR**: nice-to-have, aspirational, or a years requirement that strong depth could offset
     (years requirements are the most flexible item in a posting).
   - Don't list boilerplate ("team player") as a gap.
3. If the user might simply have forgotten to record it (it's adjacent, common for their stack, or hinted
   at elsewhere), add a **suggested addition** to the report: the exact JSON snippet and where it would go.
   It goes on a resume only after the user confirms it and approves the edit to `personal_info.json`.

## Editing `personal_info.json`

Only with explicit approval for a specific change, never as a side effect. Show the exact diff (path,
old value, new value), wait for "yes", apply it, then re-run `check.py validate ... --schema personal_info`.

## Final audit (run before rendering)

For each bullet in `tailored_resume.json`, find its source accomplishment and confirm:
- every number appears in the source `text` or `metrics`;
- every named technology appears in the source `text`, its `skills`, or the entry's `tech_stack`;
- the verb doesn't claim more ownership than the source.

Fix or drop any bullet that fails. Record any judgment calls in the report's change log.
