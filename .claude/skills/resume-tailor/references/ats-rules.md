# ATS rules

How applicant tracking systems (Workday, Greenhouse, Lever, iCIMS, Taleo) parse and score a resume, and what
that means for this skill. Jake's template already handles the layout; most of these rules are about what
goes *into* it.

## What the template guarantees (do not undo)

- Single column. Multi-column layouts get read left-to-right and interleave text.
- Plain-text section headings with standard names: **Education, Experience, Projects, Technical Skills**,
  plus **Achievements** and **Interests** when used. Never rename them to creative headers like
  "My Journey" or "Toolbox"; ATS may skip unrecognized sections.
- Contact info in the document body, not in a page header or footer (some parsers drop those).
- No images or icons. Links print as readable text (`github.com/you`), not "GitHub" or a logo.
- `\pdfgentounicode=1` (pdfLaTeX) or native Unicode (XeTeX/Tectonic) keeps the PDF text extractable.
- Standard bullets and fonts.

`render.py` produces all of this. Never hand-edit LaTeX to add tables, columns, icons, colors, or
`\fontawesome` glyphs.

## Content rules

**Dates**: one consistent format, which `render.py` enforces as "Jun. 2024 -- Present". "Present" is
recognized; "Now" and "Ongoing" often aren't.

**Names**: use the full company and school names as they appear in `personal_info.json`. Don't
abbreviate ("Amazon Web Services" for the employer, not "AWS").

**Job title alignment**: titles are factual and never changed. Alignment with the target title comes
from the skills, bullets, and keyword choice, not from editing a title.

**Keywords**:
- ATS matching is mostly exact-string. "JavaScript" is not "JS", "Node.js" is not "NodeJS", "CI/CD" is not
  "continuous integration". Use the posting's exact spelling whenever the underlying skill is supported.
- For a supported acronym, use both forms once when it's natural: "retrieval-augmented generation (RAG)".
- Required keywords should appear in at least one experience or project bullet, not only in Technical
  Skills. Skills-only mentions score lower and look unproven to a recruiter.
- Core keywords appearing 2-3 times across sections is ideal. More than about 5 mentions reads as
  stuffing, and some ATS penalize it.
- Keywords in the most recent role and in Technical Skills carry the most weight.

**Length**: strictly one page (decided for this skill). Recruiters spend about 6-8 seconds on a first pass.

**Header**: name, phone, email, and at most 3 links (LinkedIn first, then GitHub, then a portfolio or
the link most relevant to the role). Include location when `personal_info.json` has it and the posting
cares about location (on-site, hybrid, relocation); otherwise it's optional.

**Characters**: write plain text in `tailored_resume.json`. Don't use emoji, decorative Unicode bullets,
or manual LaTeX. `render.py` escapes `& % $ # _ { } ~ ^ \ < > |` and converts straight quotes.

## File-format guidance (for the report)

- ATS portal (Workday, Greenhouse, Lever): a text-based PDF from LaTeX parses well. If a portal's parser
  mangles it, that portal also accepts `.docx`; mention this as an option, but this skill doesn't produce it.
- Email or referral: PDF.
- File name: `FirstName_LastName_Resume.pdf`, or with the role appended.
