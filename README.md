# resume_tailor

An Agent Skill that tailors a one-page, ATS-friendly resume to a job posting. It reads your
`personal_info.json`, extracts the posting from a link (or pasted text), picks and truthfully rephrases
your most relevant material, and fills [Jake's resume template](https://github.com/jakegut/resume).

Works in any chat that supports Agent Skills (Claude Code, Cursor). There is nothing to run by hand:
the agent calls the bundled helper scripts itself.

## Setup

1. **Python 3.9+** on your `PATH` (standard library only, nothing to `pip install`).
2. **Your data:** copy `personal_info.example.json` to `personal_info.json` in the repo root and fill it in.
   The format is defined in
   [`.claude/skills/resume-tailor/schemas/personal_info.schema.json`](.claude/skills/resume-tailor/schemas/personal_info.schema.json).
   `personal_info.json` is gitignored.
3. **Optional, for PDFs:** install [Tectonic](https://tectonic-typesetting.github.io/en-US/install.html)
   (a single binary that downloads LaTeX packages on demand):
   - Windows: `winget install TectonicTypesetting.Tectonic` or download the release zip and put `tectonic.exe` on your `PATH`
   - macOS: `brew install tectonic`
   - Linux: `curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh`

   Without Tectonic you still get `resume.tex`, which you can paste into Overleaf.

## Usage

Open a chat in this repo and run:

```
/resume-tailor https://boards.greenhouse.io/acme/jobs/123456
```

or paste the posting text instead of a link. You can also just ask "tailor my resume to this job: <link>".

Each run writes `output/<company>-<role>-<YYYY-MM-DD>/`:

| File | Contents |
|------|----------|
| `job.json` | Extracted posting: company, title, seniority, requirements, keywords |
| `tailored_resume.json` | What was selected and how it was rephrased |
| `resume.tex` | Jake's template, filled in. Paste into Overleaf (pdfLaTeX) or compile locally |
| `resume.pdf` | Only when Tectonic is installed |
| `report.md` | Fit verdict, keyword coverage, why items were chosen, gaps, suggested additions to confirm |

After a run you can iterate in the same chat ("swap project X for Y", "emphasize backend work").
The skill never edits `personal_info.json` unless you approve a specific change.

## Using the skill in other projects

Copy `.claude/skills/resume-tailor/` into `~/.claude/skills/` (personal, every project) or into another
repo's `.claude/skills/`. Keep `personal_info.json` in the folder you open the chat in.

## Tests

```
python -m unittest discover -s .claude/skills/resume-tailor/tests -v
```

## Credits

See [`.claude/skills/resume-tailor/CREDITS.md`](.claude/skills/resume-tailor/CREDITS.md).
Jake's template is MIT-licensed (Copyright (c) 2020 Jake Gutierrez).
