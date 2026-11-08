import copy
import sys
import unittest
import urllib.parse
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES = TESTS_DIR / "fixtures"
REPO_ROOT = TESTS_DIR.parents[3]
sys.path.insert(0, str(TESTS_DIR.parent / "scripts"))

import check  # noqa: E402
import fetch_posting  # noqa: E402

EXAMPLE_INFO = REPO_ROOT / "personal_info.example.json"
JOB_FIXTURES = sorted(FIXTURES.glob("job_*.json"))


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.info = check.load_json(EXAMPLE_INFO)
        self.schema = check.load_schema("personal_info")

    def errors(self, data, schema="personal_info"):
        return check.validate(data, check.load_schema(schema))

    def test_fixtures_are_valid(self):
        self.assertEqual(self.errors(self.info), [])
        self.assertEqual(self.errors(check.load_json(FIXTURES / "tailored_resume.example.json"), "tailored_resume"), [])
        self.assertGreaterEqual(len(JOB_FIXTURES), 3)
        for path in JOB_FIXTURES:
            with self.subTest(job=path.name):
                self.assertEqual(self.errors(check.load_json(path), "job"), [])

    def test_load_json_accepts_utf16_from_powershell_redirect(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            path.write_text('{"name": "Zoë"}', encoding="utf-16")
            self.assertEqual(check.load_json(path), {"name": "Zoë"})

    def test_missing_required_field(self):
        data = copy.deepcopy(self.info)
        del data["work_experience"][0]["company"]
        self.assertIn("$.work_experience[0]: missing required field 'company'", self.errors(data))

    def test_unknown_field_catches_typos(self):
        data = copy.deepcopy(self.info)
        data["work_experience"][0]["acomplishments"] = []
        self.assertIn("$.work_experience[0]: unknown field 'acomplishments'", self.errors(data))

    def test_date_format(self):
        data = copy.deepcopy(self.info)
        data["education"][0]["dates"]["end"] = "May 2026"
        errs = self.errors(data)
        self.assertEqual(len(errs), 1)
        self.assertIn("$.education[0].dates.end", errs[0])
        data["education"][0]["dates"]["end"] = "present"
        self.assertEqual(self.errors(data), [])

    def test_accomplishment_object_reports_inner_error(self):
        data = copy.deepcopy(self.info)
        data["work_experience"][0]["accomplishments"][0] = {"skills": ["Go"]}
        self.assertIn("$.work_experience[0].accomplishments[0]: missing required field 'text'", self.errors(data))

    def test_accomplishment_wrong_type(self):
        data = copy.deepcopy(self.info)
        data["work_experience"][0]["accomplishments"][0] = 42
        self.assertEqual(self.errors(data), ["$.work_experience[0].accomplishments[0]: must match exactly one allowed form"])

    def test_extra_skill_categories_allowed_but_typed(self):
        data = copy.deepcopy(self.info)
        data["technical_skills"]["testing"] = ["pytest"]
        self.assertEqual(self.errors(data), [])
        data["technical_skills"]["testing"] = "pytest"
        self.assertIn("$.technical_skills.testing: expected array, got str", self.errors(data))

    def test_tailored_limits(self):
        data = check.load_json(FIXTURES / "tailored_resume.example.json")
        data["skills"].append({"label": "Extra", "items": ["X"]})
        data["section_order"].append("summary")
        errs = self.errors(data, "tailored_resume")
        self.assertTrue(any("$.skills: at most 4" in e for e in errs), errs)
        self.assertTrue(any("$.section_order[4]" in e for e in errs), errs)

    def test_tailored_bullet_max_length(self):
        data = check.load_json(FIXTURES / "tailored_resume.example.json")
        data["experience"][0]["roles"][0]["bullets"][0] = "x" * 241
        self.assertTrue(any("longer than 240" in e for e in self.errors(data, "tailored_resume")))


class PagesTests(unittest.TestCase):
    def test_pdf_page_counts(self):
        self.assertEqual(check.count_pdf_pages((FIXTURES / "one_page.pdf").read_bytes()), 1)
        self.assertEqual(check.count_pdf_pages((FIXTURES / "two_pages.pdf").read_bytes()), 2)

    def test_uncompressed_pdf(self):
        raw = b"%PDF-1.4\n1 0 obj << /Type /Pages /Kids [2 0 R 3 0 R] /Count 2 >> endobj\n2 0 obj << /Type /Page >> endobj\n3 0 obj << /Type /Page >> endobj\n"
        self.assertEqual(check.count_pdf_pages(raw), 2)

    def test_not_a_pdf(self):
        self.assertIsNone(check.count_pdf_pages(b"hello"))

    def test_log_line_including_wrapped_path(self):
        self.assertEqual(check.count_log_pages("...\nOutput written on resume.xdv (1 page, 29472 bytes).\n"), 1)
        self.assertEqual(check.count_log_pages("Output written on C:/a/very/long/path/that/wra\nps/resume.xdv (2 pages, 30000 bytes)."), 2)
        self.assertIsNone(check.count_log_pages("No pages of output."))

    def test_overfull_boxes(self):
        log = (
            "Overfull \\hbox (54.2pt too wide) in paragraph at lines 131--131\n"
            "Overfull \\hbox (54.2pt too wide) in paragraph at lines 131--131\n"
            "Overfull \\hbox (0.4pt too wide) in alignment at lines 140--142\n"
            "Overfull \\hbox (3.0pt too wide) detected at line 150\n"
        )
        tex_lines = [""] * 149 + ["  \\resumeProjectHeading{Wide}{2025}"]
        boxes = check.overfull_boxes(log, tex_lines)
        self.assertEqual([b["tex_line"] for b in boxes], [131, 150])
        self.assertEqual(boxes[0]["too_wide_pt"], 54.2)
        self.assertEqual(boxes[1]["source"], "\\resumeProjectHeading{Wide}{2025}")

    def test_pages_command_requires_one_page_and_no_overfull(self):
        import io
        import json
        import shutil
        import tempfile
        from contextlib import redirect_stdout

        def run(log_text):
            with tempfile.TemporaryDirectory() as tmp:
                pdf = Path(tmp) / "resume.pdf"
                shutil.copy(FIXTURES / "one_page.pdf", pdf)
                pdf.with_suffix(".log").write_text(log_text, encoding="utf-8")
                out = io.StringIO()
                with redirect_stdout(out):
                    code = check.main(["pages", str(pdf)])
                return code, json.loads(out.getvalue())

        code, result = run("Output written on resume.xdv (1 page).\n")
        self.assertEqual((code, result["ok"], result["overfull"]), (0, True, []))
        code, result = run("Overfull \\hbox (20.0pt too wide) in paragraph at lines 9--9\n")
        self.assertEqual((code, result["one_page"], result["ok"]), (2, True, False))


class KeywordTests(unittest.TestCase):
    def setUp(self):
        self.tex = (FIXTURES / "resume.example.tex").read_text(encoding="utf-8")

    def hits(self, keywords):
        return {r["term"]: r for r in check.keyword_hits({"keywords": keywords}, self.tex)["keywords"]}

    def test_sections_are_plain_text(self):
        sections = check.tex_to_sections(self.tex)
        self.assertEqual(list(sections), ["Header", "Education", "Experience", "Projects", "Technical Skills"])
        self.assertIn("Node.js & Express", sections["Experience"])
        self.assertIn("35% to 78%", sections["Experience"])
        self.assertIn("Lumen Payments - Merchant Platform", sections["Experience"])
        self.assertNotIn("\\", "".join(sections.values()))

    def test_exact_variant_missing(self):
        r = self.hits([
            {"term": "PostgreSQL", "priority": "required"},
            {"term": "Postgres", "priority": "required"},
            {"term": "idempotent", "priority": "preferred", "aliases": ["idempotency"]},
            {"term": "Rust", "priority": "preferred"},
        ])
        self.assertEqual(r["PostgreSQL"]["status"], "exact")
        self.assertEqual(set(r["PostgreSQL"]["sections"]), {"Experience", "Projects", "Technical Skills"})
        self.assertEqual(r["Postgres"]["status"], "variant")
        self.assertEqual(r["Postgres"]["variant_used"], "PostgreSQL")
        self.assertEqual(r["idempotent"]["status"], "variant")
        self.assertEqual(r["Rust"]["status"], "missing")

    def test_short_terms_are_case_sensitive_and_word_bounded(self):
        tex = r"\begin{document}\section{Experience}\resumeItem{Let's go build Django and Golang tools}"
        r = {x["term"]: x for x in check.keyword_hits({"keywords": [{"term": "Go", "priority": "required"}]}, tex)["keywords"]}
        self.assertEqual(r["Go"]["status"], "variant")
        self.assertEqual(r["Go"]["variant_used"], "Golang")

    def test_ambiguous_alias_not_used(self):
        tex = r"\begin{document}\section{Projects}\resumeItem{Kills and partitions a node to test Raft}"
        r = check.keyword_hits({"keywords": [{"term": "Node.js", "priority": "required"}]}, tex)["keywords"][0]
        self.assertEqual(r["status"], "missing")

    def test_cplusplus_and_csharp(self):
        tex = r"\begin{document}\section{Technical Skills}\textbf{Languages}{: C++, C\#, C}"
        r = {x["term"]: x for x in check.keyword_hits({"keywords": [{"term": "C++", "priority": "required"}, {"term": "C#", "priority": "required"}]}, tex)["keywords"]}
        self.assertEqual(r["C++"]["status"], "exact")
        self.assertEqual(r["C#"]["status"], "exact")

    def test_weighted_literal_coverage(self):
        summary = check.keyword_hits(check.load_json(FIXTURES / "job_backend_fintech.json"), self.tex)["summary"]
        self.assertEqual(summary["required"], {"found": 4, "exact": 4, "total": 4})
        self.assertEqual(summary["preferred"]["total"], 7)
        self.assertEqual(summary["literal_weighted_coverage_pct"], round(100 * (8 + summary["preferred"]["found"]) / 15))


class BudgetTests(unittest.TestCase):
    def test_example_fits(self):
        report = check.budget_report(check.load_json(FIXTURES / "tailored_resume.example.json"))
        self.assertTrue(report["within_budget"], report["warnings"])
        self.assertEqual(report["bullets"], 13)

    def test_overfull_resume_is_flagged(self):
        data = check.load_json(FIXTURES / "tailored_resume.example.json")
        data["projects"][0]["bullets"] += ["Wrote a fault-injection harness that kills and partitions nodes to verify linearizability"] * 10
        data["experience"][0]["roles"][0]["bullets"].append("x" * 230)
        report = check.budget_report(data)
        self.assertFalse(report["within_budget"])
        joined = " ".join(report["warnings"])
        self.assertIn("estimated", joined)
        self.assertIn("bullets (max 16)", joined)
        self.assertIn("longer than 2 lines", joined)

    def test_text_width_uses_glyph_widths(self):
        self.assertLess(check.text_width("iiiiiiiiii"), check.text_width("mmmmmmmmmm"))
        self.assertAlmostEqual(check.text_width("ab", 1.1), check.text_width("ab") * 1.1)

    def test_orphaned_bullets_are_listed_to_tighten(self):
        # These sit either side of the wrap point measured in Tectonic output (fits at 505.7pt, wraps at 512pt).
        wrapped = "Raised frontend test coverage from 35% to 78% with Jest and React Testing Library and added it to GitHub Actions"
        fits = "Raised frontend test coverage from 35% to 78% with Jest and React Testing Library, gated in GitHub Actions CI"
        self.assertTrue(check._is_orphaned(wrapped))
        self.assertFalse(check._is_orphaned(fits))
        self.assertFalse(check._is_orphaned("x" * 100 + " " + "y" * 120))

        data = check.load_json(FIXTURES / "tailored_resume.example.json")
        data["experience"][0]["roles"][0]["bullets"][0] = wrapped
        report = check.budget_report(data)
        self.assertIn(wrapped, report["tighten"])
        self.assertTrue(report["within_budget"])

    def test_wide_heading_is_a_warning(self):
        data = check.load_json(FIXTURES / "tailored_resume.example.json")
        data["projects"][0]["tech_stack"] = ["Python", "FastAPI", "OpenAI API", "PostgreSQL", "pgvector", "Docker", "React"]
        report = check.budget_report(data)
        self.assertFalse(report["within_budget"])
        self.assertTrue(any(f"heading for '{data['projects'][0]['name']}' is too wide" in w for w in report["warnings"]))


class FetchPostingOfflineTests(unittest.TestCase):
    JSON_LD_PAGE = """<html><head><title>Job</title>
    <script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"X"},
    {"@type":"JobPosting","title":"Backend Engineer","hiringOrganization":{"@type":"Organization","name":"Acme"},
    "jobLocation":[{"@type":"Place","address":{"addressLocality":"Toronto","addressRegion":"ON"}}],
    "employmentType":["FULL_TIME"],"description":"&lt;p&gt;Build &lt;b&gt;APIs&lt;/b&gt;&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Go&lt;/li&gt;&lt;li&gt;PostgreSQL&lt;/li&gt;&lt;/ul&gt;"}]}</script>
    </head><body><nav>Menu</nav><p>Body</p></body></html>"""

    def test_json_ld_in_graph(self):
        posting = fetch_posting.extract_json_ld(self.JSON_LD_PAGE)
        self.assertEqual(posting["title"], "Backend Engineer")
        self.assertEqual(posting["company"], "Acme")
        self.assertEqual(posting["location"], "Toronto, ON")
        self.assertEqual(posting["employment_type"], "FULL_TIME")
        self.assertEqual(posting["description_text"], "Build APIs\n\n- Go\n- PostgreSQL")

    def test_no_json_ld(self):
        self.assertIsNone(fetch_posting.extract_json_ld("<html><body>No data</body></html>"))

    def test_html_to_text_skips_chrome(self):
        text = fetch_posting.html_to_text("<nav>Home Jobs</nav><h1>Role</h1><script>var x=1</script><p>Do things</p><footer>(c)</footer>")
        self.assertEqual(text, "Role\n\nDo things")

    def test_board_api_urls(self):
        cases = {
            "https://job-boards.greenhouse.io/gitlab/jobs/8638232002": "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs/8638232002",
            "https://boards.greenhouse.io/stripe/jobs/123": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs/123",
            "https://careers.acme.com/jobs?gh_jid=555&for=acme": "https://boards-api.greenhouse.io/v1/boards/acme/jobs/555",
            "https://jobs.lever.co/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd": "https://api.lever.co/v0/postings/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd",
            "https://jobs.ashbyhq.com/openai/8fb1615c-34bf-47c4-a1d1-b7b2f836bbd3": "https://api.ashbyhq.com/posting-api/job-board/openai?includeCompensation=true",
            "https://acme.wd5.myworkdayjobs.com/en-US/External/job/Toronto/Engineer_R123": "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/job/Toronto/Engineer_R123",
            "https://www.linkedin.com/jobs/view/software-engineer-at-acme-4012345678/": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4012345678",
            "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4099": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4099",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                parsed = urllib.parse.urlparse(url)
                found = [s(parsed) for s in fetch_posting.BOARD_APIS]
                apis = [f[0] for f in found if f]
                self.assertEqual(apis, [expected])

    def test_unknown_host_has_no_board_api(self):
        parsed = urllib.parse.urlparse("https://example.com/careers/123")
        self.assertTrue(all(s(parsed) is None for s in fetch_posting.BOARD_APIS))

    def test_confidence(self):
        self.assertEqual(fetch_posting._confidence("short"), "low")
        self.assertEqual(fetch_posting._confidence("Please enable JavaScript to continue. " * 20), "low")
        self.assertEqual(fetch_posting._confidence("Responsibilities and requirements for this role. " * 20), "medium")


if __name__ == "__main__":
    unittest.main()
