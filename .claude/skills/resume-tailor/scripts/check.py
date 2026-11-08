#!/usr/bin/env python3
"""Deterministic helper checks for the resume-tailor skill. Standard library only.

Usage:
    python check.py validate <file.json> --schema personal_info|tailored_resume|job
    python check.py pages <resume.pdf | resume.log>
    python check.py keywords <job.json> <resume.tex>
    python check.py budget <tailored_resume.json>

Every command prints JSON to stdout. Exit codes: 0 ok, 1 invalid input or error,
2 check failed (over one page / over budget).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = SKILL_DIR / "schemas"


# ---------------------------------------------------------------------------
# JSON loading and a small JSON Schema validator
# ---------------------------------------------------------------------------

def load_json(path: Path | str):
    raw = Path(path).read_bytes()
    encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    return json.loads(raw.decode(encoding))


def load_schema(name: str) -> dict:
    path = Path(name)
    if not path.suffix:
        path = SCHEMA_DIR / f"{name}.schema.json"
    return load_json(path)


_TYPES = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def _resolve(root: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"only local $ref is supported: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _type_matches(instance, schema: dict, root: dict) -> bool:
    if "$ref" in schema:
        schema = _resolve(root, schema["$ref"])
    expected = schema.get("type")
    if expected is None:
        return True
    expected = expected if isinstance(expected, list) else [expected]
    return any(_TYPES[t](instance) for t in expected)


def validate(instance, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """Validate against the JSON Schema subset used by this skill. Returns error strings."""
    root = root if root is not None else schema
    errors: list[str] = []

    if "$ref" in schema:
        errors += validate(instance, _resolve(root, schema["$ref"]), root, path)

    if "oneOf" in schema:
        results = [validate(instance, branch, root, path) for branch in schema["oneOf"]]
        passing = [r for r in results if not r]
        if len(passing) != 1:
            typed = [r for r, b in zip(results, schema["oneOf"]) if _type_matches(instance, b, root)]
            if len(passing) == 0 and len(typed) == 1:
                errors += typed[0]
            else:
                errors.append(f"{path}: must match exactly one allowed form")

    if "type" in schema:
        expected = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](instance) for t in expected):
            return errors + [f"{path}: expected {' or '.join(expected)}, got {type(instance).__name__}"]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: must not be empty" if schema["minLength"] == 1 else f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters ({len(instance)})")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: at most {schema['maxItems']} item(s) allowed, got {len(instance)}")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], root, f"{path}[{i}]")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], root, f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unknown field '{key}'")
            elif isinstance(extra, dict):
                errors += validate(value, extra, root, f"{path}.{key}")

    return errors


def cmd_validate(args) -> int:
    try:
        data = load_json(args.file)
    except (OSError, json.JSONDecodeError) as exc:
        _emit({"valid": False, "errors": [f"cannot read {args.file}: {exc}"]})
        return 1
    errors = validate(data, load_schema(args.schema))
    _emit({"valid": not errors, "errors": errors})
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# Page counting
# ---------------------------------------------------------------------------

_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_PAGES_COUNT_RE = re.compile(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)|/Count\s+(\d+)[^>]*?/Type\s*/Pages\b", re.S)
_PAGE_RE = re.compile(rb"/Type\s*/Page(?![a-zA-Z])")
_LOG_RE = re.compile(r"Output written on .*?\(\s*(\d+)\s+pages?", re.S)


def count_pdf_pages(data: bytes) -> int | None:
    """Page count from raw PDF bytes, including compressed object streams."""
    chunks = [data]
    for match in _STREAM_RE.finditer(data):
        try:
            chunks.append(zlib.decompress(match.group(1)))
        except zlib.error:
            pass
    counts = [int(a or b) for chunk in chunks for a, b in _PAGES_COUNT_RE.findall(chunk)]
    if counts:
        return max(counts)
    pages = sum(len(_PAGE_RE.findall(chunk)) for chunk in chunks)
    return pages or None


def count_log_pages(text: str) -> int | None:
    matches = _LOG_RE.findall(text)
    return int(matches[-1]) if matches else None


_OVERFULL_RE = re.compile(r"Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)[^\n]*?lines? (\d+)")
OVERFULL_TOLERANCE_PT = 1.0


def overfull_boxes(log_text: str, tex_lines: list[str] | None = None) -> list[dict]:
    """Text that runs past the right margin. In Jake's template this is almost always a heading row."""
    seen, boxes = set(), []
    for pt, line in _OVERFULL_RE.findall(log_text):
        if float(pt) <= OVERFULL_TOLERANCE_PT or line in seen:
            continue
        seen.add(line)
        box = {"tex_line": int(line), "too_wide_pt": float(pt)}
        if tex_lines and 0 < int(line) <= len(tex_lines):
            box["source"] = tex_lines[int(line) - 1].strip()
        boxes.append(box)
    return boxes


def cmd_pages(args) -> int:
    path = Path(args.file)
    pages, source = None, None
    if path.suffix.lower() == ".pdf" and path.exists():
        pages, source = count_pdf_pages(path.read_bytes()), str(path)
    log = path if path.suffix.lower() == ".log" else path.with_suffix(".log")
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    if pages is None and log_text:
        pages, source = count_log_pages(log_text), str(log)
    if pages is None:
        _emit({"pages": None, "error": f"could not determine page count from {path}"})
        return 1
    tex = path.with_suffix(".tex")
    tex_lines = tex.read_text(encoding="utf-8").splitlines() if tex.exists() else None
    overfull = overfull_boxes(log_text, tex_lines)
    ok = pages == 1 and not overfull
    _emit({"pages": pages, "one_page": pages == 1, "overfull": overfull, "ok": ok, "source": source})
    return 0 if ok else 2


# ---------------------------------------------------------------------------
# Literal keyword hits (supplementary to the model's semantic scoring)
# ---------------------------------------------------------------------------

ALIAS_GROUPS = [
    ["JavaScript", "JS"],
    ["TypeScript", "TS"],
    ["Node.js", "NodeJS", "Node"],
    ["React", "React.js", "ReactJS"],
    ["Next.js", "NextJS"],
    ["Vue", "Vue.js", "VueJS"],
    ["Angular", "AngularJS"],
    ["Go", "Golang"],
    ["C#", "C Sharp"],
    ["C++", "CPP"],
    [".NET", "dotnet"],
    ["Python", "Python3"],
    ["PostgreSQL", "Postgres"],
    ["MongoDB", "Mongo"],
    ["Elasticsearch", "Elastic Search"],
    ["Kubernetes", "k8s"],
    ["Amazon Web Services", "AWS"],
    ["Google Cloud Platform", "GCP", "Google Cloud"],
    ["Microsoft Azure", "Azure"],
    ["AWS Lambda", "Lambda"],
    ["Amazon S3", "S3"],
    ["CI/CD", "CICD", "continuous integration", "continuous delivery", "continuous deployment"],
    ["Infrastructure as Code", "IaC"],
    ["REST", "RESTful", "REST API", "REST APIs", "RESTful APIs", "RESTful API"],
    ["microservices", "microservice", "micro-services"],
    ["machine learning", "ML"],
    ["artificial intelligence", "AI"],
    ["large language models", "large language model", "LLM", "LLMs"],
    ["natural language processing", "NLP"],
    ["retrieval-augmented generation", "retrieval augmented generation", "RAG"],
    ["object-oriented programming", "object-oriented", "OOP"],
    ["test-driven development", "TDD"],
    ["unit testing", "unit tests"],
    ["distributed systems", "distributed system"],
    ["Agile", "Scrum", "Agile/Scrum"],
]

# Aliases that are too ambiguous to search for on their own in resume prose.
_AMBIGUOUS = {"node"}


def _variants(term: str, extra: list[str]) -> list[str]:
    seen, out = set(), []
    group = next((g for g in ALIAS_GROUPS if term.lower() in (a.lower() for a in g)), [])
    for v in [term, *extra, *group]:
        key = v.lower()
        if key in seen or (key in _AMBIGUOUS and key != term.lower()):
            continue
        seen.add(key)
        out.append(v)
    return out


def _term_regex(term: str) -> re.Pattern:
    flags = 0 if len(term) <= 3 else re.IGNORECASE
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9+#])", flags)


_TEX_UNESCAPES = [
    (r"\textbackslash{}", "\\"), (r"\textasciitilde{}", "~"), (r"\textasciicircum{}", "^"),
    (r"\textless{}", "<"), (r"\textgreater{}", ">"), (r"\textbar{}", "|"),
    (r"\&", "&"), (r"\%", "%"), (r"\$", "$"), (r"\#", "#"), (r"\_", "_"), (r"\{", "{"), (r"\}", "}"),
]


def tex_to_sections(tex: str) -> dict[str, str]:
    """Plain text per section from a rendered resume.tex body."""
    body = tex.split(r"\begin{document}", 1)[-1]
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = re.sub(r"\\href\{[^}]*\}", "", body)
    sections: dict[str, str] = {}
    parts = re.split(r"\\section\{([^}]*)\}", body)
    names = ["Header", *parts[1::2]]
    for name, chunk in zip(names, parts[0::2]):
        for src, dst in _TEX_UNESCAPES:
            chunk = chunk.replace(src, f"\x00{ord(dst[0])}\x00")
        chunk = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", chunk)
        chunk = chunk.replace("$|$", " | ").replace("``", '"').replace("''", '"').replace("--", "-")
        chunk = re.sub(r"[{}\\$]", " ", chunk)
        chunk = re.sub(r"\x00(\d+)\x00", lambda m: chr(int(m.group(1))), chunk)
        sections[name] = re.sub(r"\s+", " ", chunk).strip()
    return sections


def keyword_hits(job: dict, tex: str) -> dict:
    sections = tex_to_sections(tex)
    results = []
    for kw in job.get("keywords", []):
        term = kw["term"]
        found = []
        for variant in _variants(term, kw.get("aliases", [])):
            rx = _term_regex(variant)
            where = {name: len(rx.findall(text)) for name, text in sections.items()}
            where = {k: v for k, v in where.items() if v}
            if where:
                found.append((variant, where))
        exact = next((f for f in found if f[0].lower() == term.lower()), None)
        best = exact or (found[0] if found else None)
        results.append({
            "term": term,
            "priority": kw["priority"],
            "status": "exact" if exact else ("variant" if found else "missing"),
            "variant_used": None if exact or not best else best[0],
            "count": sum(best[1].values()) if best else 0,
            "sections": sorted(best[1]) if best else [],
        })

    def tally(priority: str) -> dict:
        rows = [r for r in results if r["priority"] == priority]
        return {"found": sum(r["status"] != "missing" for r in rows), "exact": sum(r["status"] == "exact" for r in rows), "total": len(rows)}

    req, pref = tally("required"), tally("preferred")
    denom = req["total"] * 2 + pref["total"]
    coverage = round(100 * (req["found"] * 2 + pref["found"]) / denom) if denom else None
    return {"summary": {"required": req, "preferred": pref, "literal_weighted_coverage_pct": coverage}, "keywords": results}


def cmd_keywords(args) -> int:
    job = load_json(args.job)
    tex = Path(args.tex).read_text(encoding="utf-8")
    _emit(keyword_hits(job, tex))
    return 0


# ---------------------------------------------------------------------------
# One-page budget (used when Tectonic is not available)
# ---------------------------------------------------------------------------

# Widths use Computer Modern / Latin Modern glyph metrics (1/1000 em), the template's default
# font. Text is measured in pt at \small (10pt); bold is ~1.1x wider, \normalsize ~1.1x larger.
_GLYPHS = {
    **dict(zip("abcdefghijklmnopqrstuvwxyz", [500, 556, 444, 556, 444, 306, 500, 556, 278, 306, 528, 278, 833, 556, 500, 556, 528, 392, 394, 389, 556, 528, 722, 528, 528, 444])),
    **dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [750, 708, 722, 764, 681, 653, 785, 750, 361, 514, 778, 625, 917, 750, 778, 681, 778, 736, 556, 722, 750, 750, 1028, 750, 750, 611])),
    **{d: 500 for d in "0123456789"},
    " ": 333, ".": 278, ",": 278, ":": 278, ";": 278, "-": 333, "(": 389, ")": 389, "[": 278, "]": 278,
    "/": 500, "%": 833, "~": 500, "&": 778, "$": 500, "#": 833, "+": 778, "=": 778, "'": 278, '"': 500,
    "?": 472, "!": 278, "_": 500, "|": 278, "<": 778, ">": 778, "*": 500, "@": 778,
}
BOLD, NORMALSIZE = 1.1, 1.1

# Calibrated against Tectonic renders of Jake's template: bullets that fit measured <= 505.7pt,
# bullets that wrapped >= 512pt. Heading rows are 0.97\textwidth table cells that cannot wrap.
BULLET_LINE_PT = 508.0
SKILLS_LINE_PT = 530.0
HEADING_ROW_PT = 520.0
ORPHAN_PT = 90.0  # a last line shorter than this is a 1-3 word orphan
# Two different resumes both overflowed the page at 57 estimated lines; 54 leaves margin for pdfLaTeX.
BUDGET = {"max_lines": 54, "max_experience_entries": 4, "max_projects": 3, "max_total_bullets": 16, "max_bullet_lines": 2}


def text_width(text: str, scale: float = 1.0) -> float:
    """Approximate rendered width in pt at \\small."""
    return sum(_GLYPHS.get(c, 556) for c in text) / 100.0 * scale


def _lines(text: str, line_pt: float = BULLET_LINE_PT) -> int:
    return max(1, -(-int(text_width(text)) // int(line_pt)))


def _is_orphaned(text: str) -> bool:
    width = text_width(text)
    lines = _lines(text)
    return lines > 1 and width - (lines - 1) * BULLET_LINE_PT < ORPHAN_PT


def _heading_overflows(data: dict) -> list[str]:
    from render import display_url, format_range

    def dates(d) -> str:
        return format_range(d).replace(" -- ", " - ")

    rows = []  # (entry name, left text, row width in pt)
    for e in data.get("education", []):
        loc = e.get("location", "")
        rows.append((e["institution"], e["institution"], text_width(e["institution"], BOLD * NORMALSIZE) + text_width(loc, NORMALSIZE)))
        rows.append((e["institution"], e["degree"], text_width(e["degree"]) + text_width(dates(e["dates"]))))
    for e in data.get("experience", []):
        for i, role in enumerate(e["roles"]):
            team = f" - {role['team']}" if role.get("team") else ""
            if i == 0:
                company = e["company"] + team
                rows.append((e["company"], role["title"], text_width(role["title"], BOLD * NORMALSIZE) + text_width(dates(role["dates"]), NORMALSIZE)))
                rows.append((e["company"], company, text_width(company) + text_width(e.get("location", ""))))
            else:
                rows.append((e["company"], role["title"] + team, text_width(role["title"] + team) + text_width(dates(role["dates"]))))
    for p in data.get("projects", []):
        tail = f" | {', '.join(p['tech_stack'])}"
        if p.get("link"):
            tail += " | " + (p["link"].get("display") or display_url(p["link"]["url"]))
        rows.append((p["name"], p["name"] + tail, text_width(p["name"], BOLD) + text_width(tail) + text_width(dates(p.get("dates")))))

    problems = []
    for name, left, width in rows:
        width += 10  # minimum gap between the left and right cells
        if width > HEADING_ROW_PT:
            problems.append(f"heading for '{name}' is too wide ({width:.0f}pt of {HEADING_ROW_PT:.0f}pt): \"{left}\"")
    return problems


def budget_report(data: dict) -> dict:
    lines = 3  # name, contact line, spacing
    bullets: list[str] = []
    order = [s for s in data["section_order"] if data.get(s)]
    lines += 2 * len(order)  # section title + rule
    for e in data.get("education", []):
        lines += 2 + sum(_lines(d) for d in e.get("details", []))
    for e in data.get("experience", []):
        for i, role in enumerate(e["roles"]):
            lines += 2 if i == 0 else 1
            bullets += role["bullets"]
    for p in data.get("projects", []):
        lines += 1
        bullets += p["bullets"]
    lines += sum(_lines(b) for b in bullets)
    skill_rows = [f"{row['label']}: {', '.join(row['items'])}" for row in data.get("skills", [])]
    lines += sum(_lines(r, SKILLS_LINE_PT) for r in skill_rows)
    lines += sum(_lines(a) for a in data.get("achievements", [])) + (1 if data.get("achievements") else 0)
    lines += 1 if data.get("interests") else 0

    warnings = []
    if lines > BUDGET["max_lines"]:
        warnings.append(f"estimated {lines} lines; one page fits about {BUDGET['max_lines']}")
    if len(data.get("experience", [])) > BUDGET["max_experience_entries"]:
        warnings.append(f"{len(data['experience'])} experience entries (max {BUDGET['max_experience_entries']})")
    if len(data.get("projects", [])) > BUDGET["max_projects"]:
        warnings.append(f"{len(data['projects'])} projects (max {BUDGET['max_projects']})")
    if len(bullets) > BUDGET["max_total_bullets"]:
        warnings.append(f"{len(bullets)} experience/project bullets (max {BUDGET['max_total_bullets']})")
    long = [b for b in bullets if _lines(b) > BUDGET["max_bullet_lines"]]
    if long:
        warnings.append(f"{len(long)} bullet(s) longer than {BUDGET['max_bullet_lines']} lines: " + "; ".join(b[:60] + "..." for b in long))
    warnings += _heading_overflows(data)

    details = [d for e in data.get("education", []) for d in e.get("details", [])]
    tighten = [b for b in bullets + details + data.get("achievements", []) if _is_orphaned(b)]
    tighten += [r for r in skill_rows if _lines(r, SKILLS_LINE_PT) > 1]
    return {
        "estimated_lines": lines,
        "bullets": len(bullets),
        "budget": BUDGET,
        "within_budget": not warnings,
        "warnings": warnings,
        "tighten": tighten,
    }


def cmd_budget(args) -> int:
    report = budget_report(load_json(args.file))
    _emit(report)
    return 0 if report["within_budget"] else 2


# ---------------------------------------------------------------------------

def _emit(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate a JSON file against a skill schema")
    p.add_argument("file")
    p.add_argument("--schema", required=True, help="personal_info, tailored_resume, job, or a schema path")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("pages", help="count pages of a compiled resume")
    p.add_argument("file", help="resume.pdf (or the Tectonic resume.log)")
    p.set_defaults(func=cmd_pages)

    p = sub.add_parser("keywords", help="literal keyword hits of job.json keywords in resume.tex")
    p.add_argument("job")
    p.add_argument("tex")
    p.set_defaults(func=cmd_keywords)

    p = sub.add_parser("budget", help="estimate whether tailored_resume.json fits on one page")
    p.add_argument("file")
    p.set_defaults(func=cmd_budget)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
