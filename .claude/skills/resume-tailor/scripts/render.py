#!/usr/bin/env python3
"""Render tailored_resume.json into resume.tex using Jake's resume template.

Usage:
    python render.py <tailored_resume.json> [-o resume.tex]

The JSON is validated against schemas/tailored_resume.schema.json first. All text
fields are plain text; this script does every bit of LaTeX escaping.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PREAMBLE_PATH = SKILL_DIR / "templates" / "jake_preamble.tex"

sys.path.insert(0, str(SCRIPT_DIR))
from check import load_json, load_schema, validate  # noqa: E402

SECTION_TITLES = {
    "education": "Education",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Technical Skills",
    "achievements": "Achievements",
    "interests": "Interests",
}

MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
    "|": r"\textbar{}",
}
_ESCAPE_RE = re.compile("|".join(re.escape(c) for c in _ESCAPES))
_OPEN_QUOTE_RE = re.compile(r'(^|[\s(\[])"')


def escape(text: str) -> str:
    """Escape plain text for LaTeX body content."""
    text = _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group()], text)
    text = _OPEN_QUOTE_RE.sub(lambda m: m.group(1) + "``", text)
    return text.replace('"', "''")


def escape_url(url: str) -> str:
    """Escape a URL for the first argument of \\href."""
    return url.replace("\\", "/").replace("%", r"\%").replace("#", r"\#")


def display_url(url: str) -> str:
    """linkedin.com/in/x style text for a URL."""
    shown = re.sub(r"^(https?://|mailto:)", "", url)
    shown = re.sub(r"^www\.", "", shown)
    return shown.rstrip("/")


def format_month(value: str) -> str:
    if value == "present":
        return "Present"
    year, month = value.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def format_range(dates: dict | None) -> str:
    if not dates:
        return ""
    start, end = format_month(dates["start"]), format_month(dates["end"])
    return start if start == end else f"{start} -- {end}"


def href(url: str, text: str) -> str:
    return rf"\href{{{escape_url(url)}}}{{\underline{{{escape(text)}}}}}"


def item_list(bullets: list[str], indent: str) -> list[str]:
    if not bullets:
        return []
    lines = [f"{indent}\\resumeItemListStart"]
    lines += [f"{indent}  \\resumeItem{{{escape(b)}}}" for b in bullets]
    lines.append(f"{indent}\\resumeItemListEnd")
    return lines


def render_header(header: dict) -> list[str]:
    parts = []
    if header.get("location"):
        parts.append(escape(header["location"]))
    if header.get("phone"):
        parts.append(escape(header["phone"]))
    if header.get("email"):
        parts.append(href(f"mailto:{header['email']}", header["email"]))
    for link in header.get("links", []):
        parts.append(href(link["url"], link.get("display") or display_url(link["url"])))

    lines = [
        "%----------HEADING----------",
        r"\begin{center}",
        rf"    \textbf{{\Huge \scshape {escape(header['name'])}}} \\ \vspace{{1pt}}",
    ]
    if parts:
        lines.append("    \\small " + " $|$\n    ".join(parts))
    lines.append(r"\end{center}")
    return lines


def render_education(entries: list[dict]) -> list[str]:
    lines = [r"  \resumeSubHeadingListStart"]
    for e in entries:
        lines += [
            r"    \resumeSubheading",
            f"      {{{escape(e['institution'])}}}{{{escape(e.get('location', ''))}}}",
            f"      {{{escape(e['degree'])}}}{{{format_range(e['dates'])}}}",
        ]
        lines += item_list(e.get("details", []), "      ")
    lines.append(r"  \resumeSubHeadingListEnd")
    return lines


def render_experience(entries: list[dict]) -> list[str]:
    lines = [r"  \resumeSubHeadingListStart"]
    for e in entries:
        first, *others = e["roles"]
        company = escape(e["company"])
        if first.get("team"):
            company += " -- " + escape(first["team"])
        lines += [
            "",
            r"    \resumeSubheading",
            f"      {{{escape(first['title'])}}}{{{format_range(first['dates'])}}}",
            f"      {{{company}}}{{{escape(e.get('location', ''))}}}",
        ]
        lines += item_list(first["bullets"], "      ")
        for role in others:
            title = escape(role["title"])
            if role.get("team"):
                title += " -- " + escape(role["team"])
            lines += [
                r"    \resumeSubSubheading",
                f"      {{{title}}}{{{format_range(role['dates'])}}}",
            ]
            lines += item_list(role["bullets"], "      ")
    lines.append(r"  \resumeSubHeadingListEnd")
    return lines


def render_projects(entries: list[dict]) -> list[str]:
    lines = [r"    \resumeSubHeadingListStart"]
    for p in entries:
        heading = rf"\textbf{{{escape(p['name'])}}}"
        if p.get("tech_stack"):
            heading += rf" $|$ \emph{{{escape(', '.join(p['tech_stack']))}}}"
        if p.get("link"):
            link = p["link"]
            heading += " $|$ " + href(link["url"], link.get("display") or display_url(link["url"]))
        lines += [
            r"      \resumeProjectHeading",
            f"          {{{heading}}}{{{format_range(p.get('dates'))}}}",
        ]
        lines += item_list(p["bullets"], "          ")
    lines.append(r"    \resumeSubHeadingListEnd")
    return lines


def render_skills(rows: list[dict]) -> list[str]:
    body = [rf"     \textbf{{{escape(r['label'])}}}{{: {escape(', '.join(r['items']))}}}" for r in rows]
    return [
        r" \begin{itemize}[leftmargin=0.15in, label={}]",
        r"    \small{\item{",
        " \\\\\n".join(body),
        r"    }}",
        r" \end{itemize}",
    ]


def render_achievements(bullets: list[str]) -> list[str]:
    return [
        r"  \resumeSubHeadingListStart",
        r"    \item",
        *item_list(bullets, "      "),
        r"  \resumeSubHeadingListEnd",
    ]


def render_interests(items: list[str]) -> list[str]:
    return [
        r" \begin{itemize}[leftmargin=0.15in, label={}]",
        rf"    \small{{\item{{{escape(', '.join(items))}}}}}",
        r" \end{itemize}",
    ]


RENDERERS = {
    "education": render_education,
    "experience": render_experience,
    "projects": render_projects,
    "skills": render_skills,
    "achievements": render_achievements,
    "interests": render_interests,
}


def render(data: dict, preamble: str | None = None) -> str:
    order = data["section_order"]
    if len(set(order)) != len(order):
        raise ValueError(f"section_order has duplicates: {order}")

    if preamble is None:
        preamble = PREAMBLE_PATH.read_text(encoding="utf-8")

    out = [preamble.rstrip("\n"), "", "", r"\begin{document}", ""]
    out += render_header(data["header"])
    for key in order:
        content = data.get(key)
        if not content:
            continue
        out += ["", "", f"%-----------{SECTION_TITLES[key].upper()}-----------", rf"\section{{{SECTION_TITLES[key]}}}"]
        out += RENDERERS[key](content)
    out += ["", "", "%-------------------------------------------", r"\end{document}", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="tailored_resume.json")
    parser.add_argument("-o", "--output", type=Path, help="Output .tex path (default: resume.tex next to the input)")
    args = parser.parse_args(argv)

    data = load_json(args.input)
    errors = validate(data, load_schema("tailored_resume"))
    if errors:
        print(f"{args.input} is not a valid tailored resume:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    try:
        tex = render(data)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = args.output or args.input.with_name("resume.tex")
    output.write_text(tex, encoding="utf-8", newline="\n")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
