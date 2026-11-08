# Credits

This skill is an original combination of ideas from the MIT-licensed projects below. No code was copied
from the three resume skills; their workflows, rules, and rubrics were studied and rewritten for a
JSON-in, Jake's-LaTeX-out pipeline. Jake's template preamble is included nearly verbatim.

| Project | What we used | License |
|---------|--------------|---------|
| [jakegut/resume](https://github.com/jakegut/resume) (based on [sb2nov/resume](https://github.com/sb2nov/resume)) | `templates/jake_preamble.tex`: layout, custom commands, section formatting | MIT, Copyright (c) 2020 Jake Gutierrez |
| [nishilbhave/ats-resume-tailor](https://github.com/nishilbhave/ats-resume-tailor) | Sequential pipeline (analysis, gap analysis, rewrite, diff, ATS score, synthesis); JD requirement categories; gap severity levels; XYZ bullet formula; keyword audit statuses; weighted keyword coverage formula | MIT, Copyright (c) 2026 Nishil Bhave |
| [rshivam973/resume-tailor](https://github.com/rshivam973/resume-tailor) | Truthfulness policy (allowed vs. confirmation-required changes); "could a recruiter make you defend this sentence?" check; URL extraction order, JSON-LD preference, and confidence signals | MIT, Copyright (c) 2026 Shivam Rajput |
| [zebbern/claude-code-guide `skills/cv-tailor`](https://github.com/zebbern/claude-code-guide/tree/main/skills/cv-tailor) | ATS formatting and content-structure checklists; keyword categories (hard, soft, domain); coverage benchmarks; final quality checklist | MIT, Copyright (c) 2026 resume-optimizer contributors |

## MIT License (applies to each project above, with its own copyright line)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
