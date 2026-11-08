# `report.md` format

Write `report.md` in the run folder with these sections, in this order. Keep it scannable: tables for
lists, one-line reasons. Scores are **model-led** (your semantic judgment using the rubric below);
`check.py keywords` output is included as a literal-match cross-check, not as the score.

````markdown
# <Role title> at <Company>: tailoring report

Generated <YYYY-MM-DD> from <source url or "pasted text"> (extraction: <method>, <confidence>).

## Summary

- **Fit**: <match %> (<VERDICT>). Use STRONG_MATCH (85+), STRONG_WITH_GAPS (70-84), MODERATE_MATCH (55-69),
  WEAK_MATCH (40-54), or POOR_FIT (under 40).
- **Top strength**: <single best match between the candidate and the role>
- **Critical gap**: <most important unmet requirement, or "none">
- **Recommendation**: <apply as is / apply and address <gap> in a cover letter or referral / consider
  building <skill> first>
- **Output**: `resume.tex` (<compiled to 1-page resume.pdf | not compiled: Tectonic unavailable>)

## Requirement coverage

| Requirement | Required? | Evidence on resume | Status |
|-------------|-----------|--------------------|--------|
| Proficiency in Go, Java, or Python | yes | Lumen Payments bullets 1-3 (Go), tinykv | MET |
| Kafka or event streaming | no | Lumen Payments bullet 1 | MET |
| Terraform | no | Technical Skills only | PARTIAL (skills only) |
| Payments experience | no | Lumen Payments (payouts) | MET |
| Kubernetes in production | yes | none | GAP (see below) |

Status values: MET (shown in a bullet), PARTIAL (only in skills, or adjacent evidence), GAP.

## Keyword coverage

Model-led score: **<weighted %>** (required keywords count double:
`(met_required * 2 + met_preferred) / (total_required * 2 + total_preferred)`, where "met" means the
keyword or a true synonym is demonstrated on the resume).

Literal cross-check (`check.py keywords`): required <found>/<total> (exact <n>), preferred <found>/<total>,
literal weighted <pct>%.

| Keyword | Priority | Literal status | Where | Note |
|---------|----------|----------------|-------|------|
| PostgreSQL | required | exact | Experience, Projects, Skills | |
| idempotent | preferred | variant ("idempotency") | Experience | fine; same concept |
| observability | preferred | missing | | Grafana dashboards bullet shows it; consider the exact word |

Flag every `variant` where switching to the posting's exact spelling would be truthful, and every
`missing` keyword the candidate does support (wording fix), separately from true gaps.

## What was selected and why

| Section | Item | Why |
|---------|------|-----|
| Experience | Lumen Payments, SWE Intern (4 bullets) | Go + Kafka + PostgreSQL + payments domain; most recent |
| Projects | tinykv | Only evidence of distributed-systems fundamentals (required) |
| Left out | Spotify Mood Mixer | No overlap with the posting; space |

Section order used: <order> because <career-stage reason>.

## Change log

| # | Entry | Source accomplishment | Resume bullet | Change |
|---|-------|-----------------------|---------------|--------|
| 1 | Lumen Payments | "Wrote gRPC load tests and tuned PostgreSQL indexes..." + metric "p95 latency reduced from 420ms to 90ms" | "Reduced p95 latency of the merchant balance gRPC endpoint from 420ms to 90ms..." | Result-first (XYZ), metric from `metrics` |

Change types: kept, rephrased, reordered, merged, terminology (posting spelling), dropped.

## Gaps

| Requirement | Severity | Adjacent evidence | Suggested mitigation |
|-------------|----------|-------------------|----------------------|
| Kubernetes in production | SIGNIFICANT | Deployed with Helm to a team cluster (intern) | Mention it in a cover letter or recruiter note; a small K8s project would close it |

Severity: DEAL-BREAKER, SIGNIFICANT, or MINOR (see `truthfulness.md`). Omit boilerplate.

## Suggested additions to `personal_info.json` (need your confirmation)

Only facts the user may have and forgot to record. Never add these to the resume until confirmed.

1. Did you use **Terraform** at Brightpath? If so, add to `work_experience[1].tech_stack`:
   `"Terraform"`. Then it can appear in the infra bullet.

## Verification checklist

- [ ] Every number on the resume matches your records
- [ ] Titles, dates, and company names are exact
- [ ] <any judgment call, such as "'Led tutorials' kept, not upgraded to 'Taught'">

## Next steps

- Review `resume.tex` / `resume.pdf`; ask for changes ("swap tinykv for DocuChat", "emphasize backend").
- Overleaf: New Project > Blank Project, paste `resume.tex` into `main.tex`, compile with pdfLaTeX (default).
- Submit as `<First>_<Last>_Resume.pdf`.
````

## Scoring guidance

- **Fit %**: weight required requirements most. Start from the requirement-coverage table: each required
  requirement MET = full credit, PARTIAL = half credit, GAP = none (a DEAL-BREAKER gap caps fit at 54%).
  Preferred requirements add up to 20% of the total. Adjust by at most ±10 for seniority or domain match
  and say why.
- Don't let the literal cross-check inflate the model score. A keyword that appears only because of a
  company name ("Lumen Payments" matching "payments") doesn't count as demonstrated.
- Small wording edits during iteration should move the score by only a few points. If one moves it more,
  explain why.
