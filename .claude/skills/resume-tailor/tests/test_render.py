import copy
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES = TESTS_DIR / "fixtures"
sys.path.insert(0, str(TESTS_DIR.parent / "scripts"))

import render  # noqa: E402
from check import load_json  # noqa: E402

MINIMAL = {
    "header": {"name": "Pat Lee", "email": "pat@example.com"},
    "section_order": ["experience", "skills"],
    "education": [],
    "experience": [],
    "skills": [{"label": "Languages", "items": ["Python"]}],
}


def body(tex: str) -> str:
    return tex.split(r"\begin{document}", 1)[1]


def unescaped_braces_balance(tex: str) -> int:
    stripped = re.sub(r"\\[{}]", "", re.sub(r"(?<!\\)%.*", "", tex))
    return stripped.count("{") - stripped.count("}")


class EscapeTests(unittest.TestCase):
    def test_every_special_character(self):
        cases = {
            "R&D": r"R\&D",
            "50%": r"50\%",
            "$2M": r"\$2M",
            "C#": r"C\#",
            "snake_case": r"snake\_case",
            "{x}": r"\{x\}",
            "~1K": r"\textasciitilde{}1K",
            "2^10": r"2\textasciicircum{}10",
            "a\\b": r"a\textbackslash{}b",
            "<5ms": r"\textless{}5ms",
            ">99%": r"\textgreater{}99\%",
            "a|b": r"a\textbar{}b",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(render.escape(raw), expected)

    def test_backslash_replacement_is_not_double_escaped(self):
        self.assertEqual(render.escape("\\{"), r"\textbackslash{}\{")

    def test_straight_quotes_become_latex_pairs(self):
        self.assertEqual(render.escape('Named "best app" by users'), "Named ``best app'' by users")
        self.assertEqual(render.escape('"Quoted" start'), "``Quoted'' start")

    def test_plain_text_is_unchanged(self):
        self.assertEqual(render.escape("Built a Go service, cutting delay by 5x."), "Built a Go service, cutting delay by 5x.")

    def test_url_escaping_for_href(self):
        self.assertEqual(render.escape_url("https://x.dev/a%20b#top"), r"https://x.dev/a\%20b\#top")


class FormattingTests(unittest.TestCase):
    def test_months_follow_jakes_style(self):
        self.assertEqual(render.format_month("2024-06"), "June 2024")
        self.assertEqual(render.format_month("2018-08"), "Aug. 2018")
        self.assertEqual(render.format_month("2021-05"), "May 2021")
        self.assertEqual(render.format_month("present"), "Present")

    def test_ranges(self):
        self.assertEqual(render.format_range({"start": "2024-05", "end": "present"}), "May 2024 -- Present")
        self.assertEqual(render.format_range({"start": "2024-05", "end": "2024-05"}), "May 2024")
        self.assertEqual(render.format_range(None), "")

    def test_display_url(self):
        self.assertEqual(render.display_url("https://www.linkedin.com/in/pat/"), "linkedin.com/in/pat")
        self.assertEqual(render.display_url("http://github.com/pat"), "github.com/pat")


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.example = load_json(FIXTURES / "tailored_resume.example.json")

    def test_matches_golden_file(self):
        golden = (FIXTURES / "resume.example.tex").read_text(encoding="utf-8")
        self.assertEqual(render.render(self.example), golden, "re-render the golden file if this change is intended")

    def test_document_is_well_formed(self):
        tex = render.render(self.example)
        self.assertTrue(tex.lstrip().startswith("%"))
        self.assertIn(r"\documentclass[letterpaper,11pt]{article}", tex)
        self.assertEqual(tex.count(r"\begin{document}"), 1)
        self.assertTrue(tex.rstrip().endswith(r"\end{document}"))
        self.assertEqual(unescaped_braces_balance(tex), 0)
        self.assertEqual(tex.count(r"\resumeItemListStart"), tex.count(r"\resumeItemListEnd"))
        self.assertEqual(tex.count(r"\resumeSubHeadingListStart"), tex.count(r"\resumeSubHeadingListEnd"))

    def test_preamble_keeps_tectonic_guard(self):
        tex = render.render(self.example)
        self.assertIn("\\ifdefined\\pdfgentounicode\n  \\pdfgentounicode=1\n\\fi", tex)
        self.assertNotRegex(tex, r"(?m)^\\pdfgentounicode=1")

    def test_sections_follow_section_order(self):
        data = copy.deepcopy(self.example)
        data["section_order"] = ["skills", "experience", "education", "projects"]
        titles = re.findall(r"\\section\{([^}]*)\}", render.render(data))
        self.assertEqual(titles, ["Technical Skills", "Experience", "Education", "Projects"])

    def test_sections_not_in_order_or_empty_are_skipped(self):
        data = copy.deepcopy(self.example)
        data["section_order"] = ["experience", "projects", "achievements"]
        data["projects"] = []
        titles = re.findall(r"\\section\{([^}]*)\}", render.render(data))
        self.assertEqual(titles, ["Experience"])

    def test_duplicate_sections_are_rejected(self):
        data = copy.deepcopy(self.example)
        data["section_order"] = ["experience", "experience"]
        with self.assertRaises(ValueError):
            render.render(data)

    def test_header_parts_and_links(self):
        data = copy.deepcopy(MINIMAL)
        data["header"].update(phone="555-0100", location="Austin, TX", links=[{"url": "https://github.com/pat"}, {"url": "https://pat.dev", "display": "pat.dev/work"}])
        tex = body(render.render(data))
        self.assertIn(r"\textbf{\Huge \scshape Pat Lee}", tex)
        self.assertIn(r"Austin, TX $|$", tex)
        self.assertIn(r"\href{mailto:pat@example.com}{\underline{pat@example.com}}", tex)
        self.assertIn(r"\href{https://github.com/pat}{\underline{github.com/pat}}", tex)
        self.assertIn(r"\href{https://pat.dev}{\underline{pat.dev/work}}", tex)

    def test_multiple_roles_at_one_company(self):
        data = copy.deepcopy(MINIMAL)
        data["experience"] = [{
            "company": "Acme",
            "location": "Remote",
            "roles": [
                {"title": "Software Engineer II", "team": "Payments", "dates": {"start": "2024-01", "end": "present"}, "bullets": ["Led payments work"]},
                {"title": "Software Engineer I", "dates": {"start": "2022-06", "end": "2023-12"}, "bullets": ["Built billing"]},
            ],
        }]
        tex = body(render.render(data))
        self.assertEqual(tex.count(r"\resumeSubheading"), 1)
        self.assertEqual(tex.count(r"\resumeSubSubheading"), 1)
        self.assertIn("{Software Engineer II}{Jan. 2024 -- Present}", tex)
        self.assertIn("{Acme -- Payments}{Remote}", tex)
        self.assertIn("{Software Engineer I}{June 2022 -- Dec. 2023}", tex)

    def test_project_heading_with_link_and_no_dates(self):
        data = copy.deepcopy(MINIMAL)
        data["section_order"] = ["projects"]
        data["projects"] = [{"name": "C# Tools", "tech_stack": [".NET", "C#"], "link": {"url": "https://github.com/pat/tools"}, "bullets": ["Shipped 100% test coverage"]}]
        tex = body(render.render(data))
        self.assertIn(r"{\textbf{C\# Tools} $|$ \emph{.NET, C\#} $|$ \href{https://github.com/pat/tools}{\underline{github.com/pat/tools}}}{}", tex)
        self.assertIn(r"\resumeItem{Shipped 100\% test coverage}", tex)

    def test_skills_achievements_interests(self):
        data = copy.deepcopy(MINIMAL)
        data["section_order"] = ["skills", "achievements", "interests"]
        data["skills"] = [{"label": "Languages", "items": ["C++", "Go"]}, {"label": "Tools & Platforms", "items": ["Git"]}]
        data["achievements"] = ["1st of 60 teams at HackNorth"]
        data["interests"] = ["Climbing", "Film photography"]
        tex = body(render.render(data))
        self.assertIn("\\textbf{Languages}{: C++, Go} \\\\\n     \\textbf{Tools \\& Platforms}{: Git}", tex)
        self.assertIn(r"\resumeItem{1st of 60 teams at HackNorth}", tex)
        self.assertIn(r"\small{\item{Climbing, Film photography}}", tex)

    def test_entries_without_bullets_have_no_empty_lists(self):
        data = copy.deepcopy(MINIMAL)
        data["section_order"] = ["education"]
        data["education"] = [{"institution": "State U", "degree": "B.S. Computer Science", "dates": {"start": "2020-09", "end": "2024-05"}}]
        tex = body(render.render(data))
        self.assertNotIn(r"\resumeItemListStart", tex)


class CliTests(unittest.TestCase):
    def test_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "resume.tex"
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                code = render.main([str(FIXTURES / "tailored_resume.example.json"), "-o", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(out.read_text(encoding="utf-8"), (FIXTURES / "resume.example.tex").read_text(encoding="utf-8"))

    def test_rejects_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            data = copy.deepcopy(MINIMAL)
            data["header"]["links"] = [{"url": f"https://x{i}.dev"} for i in range(4)]
            bad.write_text(json.dumps(data), encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = render.main([str(bad), "-o", str(Path(tmp) / "out.tex")])
            self.assertEqual(code, 1)
            self.assertIn("at most 3", err.getvalue())
            self.assertFalse((Path(tmp) / "out.tex").exists())


if __name__ == "__main__":
    unittest.main()
