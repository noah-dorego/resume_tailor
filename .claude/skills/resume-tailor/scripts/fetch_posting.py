#!/usr/bin/env python3
"""Fetch a job posting URL and extract its text. Standard library only.

Usage:
    python fetch_posting.py <url> [-o raw_posting.json]

Tries, in order:
  1. JobPosting JSON-LD embedded in the page
  2. Visible page text
  3. Public job-board APIs (Greenhouse, Lever, Ashby, Workday, LinkedIn guest)
  4. Gives up with confidence "low" so the agent can try a browser tool or ask the user to paste

Prints JSON: {method, confidence, url, effective_url, attempted, warnings, posting}.
Exit code 0 when usable text was found (confidence medium or high), 2 otherwise.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
TIMEOUT = 20
MIN_DESCRIPTION_CHARS = 400
BLOCKER_PHRASES = ("enable javascript", "access denied", "captcha", "sign in to", "log in to", "are you a robot", "page not found", "no longer available", "job has expired")


# ---------------------------------------------------------------------------
# HTTP and HTML helpers
# ---------------------------------------------------------------------------

def http_get(url: str) -> tuple[str, str]:
    """Return (final_url, body)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.geturl(), resp.read().decode(charset, errors="replace")


_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "header", "footer", "table"}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "iframe", "template", "form", "button"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self.skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "li" and not self.skip_depth:
            self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS and not self.skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS and tag != "li" and not self.skip_depth:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [re.sub(r"[ \t\u00a0]+", " ", line).strip() for line in raw.splitlines()]
        out: list[str] = []
        for line in lines:
            if line in ("", "-"):
                if out and out[-1] != "":
                    out.append("")
                continue
            out.append(line)
        return "\n".join(out).strip()


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    return parser.text()


def page_title(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    return parser.title.strip()


# ---------------------------------------------------------------------------
# Strategy 1: JSON-LD
# ---------------------------------------------------------------------------

_LD_RE = re.compile(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.S | re.I)


def _walk_ld(node):
    if isinstance(node, list):
        for item in node:
            yield from _walk_ld(item)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from _walk_ld(node["@graph"])


def _is_job_posting(node: dict) -> bool:
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return "JobPosting" in kinds


def _ld_location(loc) -> str:
    locs = loc if isinstance(loc, list) else [loc]
    names = []
    for item in locs:
        if not isinstance(item, dict):
            continue
        addr = item.get("address", item)
        if isinstance(addr, dict):
            parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry") if isinstance(addr.get("addressCountry"), str) else None]
            name = ", ".join(p for p in parts if p)
            if name:
                names.append(name)
    return "; ".join(dict.fromkeys(names))


def extract_json_ld(markup: str) -> dict | None:
    for block in _LD_RE.findall(markup):
        data = None
        for candidate in (block.strip(), html.unescape(block.strip())):
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if data is None:
            continue
        for node in _walk_ld(data):
            if not _is_job_posting(node):
                continue
            org = node.get("hiringOrganization") or {}
            description = html_to_text(html.unescape(node.get("description", "")))
            employment = node.get("employmentType")
            return {
                "title": node.get("title"),
                "company": org.get("name") if isinstance(org, dict) else org,
                "location": _ld_location(node.get("jobLocation")) or (node.get("jobLocationType") or None),
                "employment_type": ", ".join(employment) if isinstance(employment, list) else employment,
                "date_posted": node.get("datePosted"),
                "description_text": description,
            }
    return None


# ---------------------------------------------------------------------------
# Strategy 3: job-board APIs
# ---------------------------------------------------------------------------

def _greenhouse(url: urllib.parse.ParseResult):
    query = urllib.parse.parse_qs(url.query)
    m = re.match(r"^/(?:embed/)?([^/]+)/jobs/(\d+)", url.path)
    if m and "greenhouse.io" in url.netloc:
        board, job_id = m.groups()
    elif "gh_jid" in query and "for" in query:
        board, job_id = query["for"][0], query["gh_jid"][0]
    elif "token" in query and "for" in query and "greenhouse.io" in url.netloc:
        board, job_id = query["for"][0], query["token"][0]
    else:
        return None
    api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"

    def parse(body: str) -> dict:
        d = json.loads(body)
        return {
            "title": d.get("title"),
            "company": d.get("company_name") or board,
            "location": (d.get("location") or {}).get("name"),
            "employment_type": None,
            "date_posted": d.get("first_published") or d.get("updated_at"),
            "description_text": html_to_text(html.unescape(d.get("content", ""))),
        }
    return api, parse


def _lever(url: urllib.parse.ParseResult):
    m = re.match(r"^/([^/]+)/([0-9a-f-]{36})", url.path)
    if "lever.co" not in url.netloc or not m:
        return None
    company, job_id = m.groups()
    api = f"https://api.lever.co/v0/postings/{company}/{job_id}"

    def parse(body: str) -> dict:
        d = json.loads(body)
        sections = [d.get("descriptionPlain", "")]
        for lst in d.get("lists", []):
            sections.append(f"{lst.get('text', '')}\n{html_to_text(lst.get('content', ''))}")
        sections.append(d.get("additionalPlain", ""))
        cats = d.get("categories") or {}
        return {
            "title": d.get("text"),
            "company": company,
            "location": cats.get("location"),
            "employment_type": cats.get("commitment"),
            "date_posted": None,
            "description_text": "\n\n".join(s.strip() for s in sections if s and s.strip()),
        }
    return api, parse


def _ashby(url: urllib.parse.ParseResult):
    m = re.match(r"^/([^/]+)/([0-9a-f-]{36})", url.path)
    if "ashbyhq.com" not in url.netloc or not m:
        return None
    org, job_id = m.groups()
    api = f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true"

    def parse(body: str) -> dict:
        jobs = json.loads(body).get("jobs", [])
        job = next((j for j in jobs if j.get("id") == job_id or job_id in (j.get("jobUrl") or "")), None)
        if job is None:
            raise ValueError(f"job {job_id} not found on the {org} Ashby board")
        text = job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml", ""))
        return {
            "title": job.get("title"),
            "company": org,
            "location": job.get("location"),
            "employment_type": job.get("employmentType"),
            "date_posted": job.get("publishedAt"),
            "description_text": text,
        }
    return api, parse


def _workday(url: urllib.parse.ParseResult):
    host = re.match(r"^([^.]+)\.wd\d+\.myworkdayjobs\.com$", url.netloc)
    path = re.match(r"^/(?:[a-z]{2}-[A-Z]{2}/)?([^/]+)/(job/.+)$", url.path)
    if not host or not path:
        return None
    tenant = host.group(1)
    site, rest = path.groups()
    api = f"{url.scheme}://{url.netloc}/wday/cxs/{tenant}/{site}/{rest}"

    def parse(body: str) -> dict:
        d = json.loads(body)
        info = d.get("jobPostingInfo", {})
        return {
            "title": info.get("title"),
            "company": (d.get("hiringOrganization") or {}).get("name") or tenant,
            "location": info.get("location"),
            "employment_type": info.get("timeType"),
            "date_posted": info.get("startDate"),
            "description_text": html_to_text(info.get("jobDescription", "")),
        }
    return api, parse


def _linkedin(url: urllib.parse.ParseResult):
    if "linkedin.com" not in url.netloc:
        return None
    query = urllib.parse.parse_qs(url.query)
    m = re.search(r"/jobs/view/(?:[^/]*?-)?(\d+)", url.path)
    job_id = query.get("currentJobId", [None])[0] or (m.group(1) if m else None)
    if not job_id:
        return None
    api = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    def parse(body: str) -> dict:
        title = re.search(r"<h2[^>]*top-card-layout__title[^>]*>(.*?)</h2>", body, re.S)
        company = re.search(r"topcard__org-name-link[^>]*>(.*?)</a>", body, re.S)
        location = re.search(r"topcard__flavor--bullet[^>]*>(.*?)</span>", body, re.S)
        desc = re.search(r"<div[^>]*show-more-less-html__markup[^>]*>(.*?)</div>", body, re.S)
        clean = lambda m: html_to_text(m.group(1)) if m else None  # noqa: E731
        return {
            "title": clean(title),
            "company": clean(company),
            "location": clean(location),
            "employment_type": None,
            "date_posted": None,
            "description_text": clean(desc) or html_to_text(body),
        }
    return api, parse


BOARD_APIS = [_greenhouse, _lever, _ashby, _workday, _linkedin]


# ---------------------------------------------------------------------------

def _confidence(text: str) -> str:
    lowered = text.lower()
    blocked = len(text) < 3000 and any(p in lowered for p in BLOCKER_PHRASES)
    return "low" if len(text) < MIN_DESCRIPTION_CHARS or blocked else "medium"


def _board_api(result: dict, url: str) -> dict | None:
    parsed = urllib.parse.urlparse(url)
    for strategy in BOARD_APIS:
        found = strategy(parsed)
        if not found:
            continue
        api, parse = found
        result["attempted"].append(api)
        try:
            _, body = http_get(api)
            posting = parse(body)
            if len(posting.get("description_text") or "") >= MIN_DESCRIPTION_CHARS:
                return posting
            result["warnings"].append(f"{api} returned a short description")
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            result["warnings"].append(f"{api} failed: {exc}")
        return None
    return None


def fetch(url: str) -> dict:
    """JSON-LD first; then the board API for known hosts (cleaner than scraped text); then page text."""
    result = {"method": None, "confidence": "low", "url": url, "effective_url": None, "attempted": [url], "warnings": [], "posting": None}
    page_text = None

    try:
        final_url, markup = http_get(url)
        result["effective_url"] = final_url
        ld = extract_json_ld(markup)
        if ld and len(ld["description_text"]) >= MIN_DESCRIPTION_CHARS:
            result.update(method="json-ld", confidence="high", posting=ld)
            return result
        if ld:
            result["warnings"].append("JSON-LD JobPosting found but its description is short")
        text = html_to_text(markup)
        page_text = {"title": page_title(markup) or None, "company": None, "location": None, "employment_type": None, "date_posted": None, "description_text": text}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        result["warnings"].append(f"fetching the page failed: {exc}")

    posting = _board_api(result, result["effective_url"] or url)
    if posting is None and result["effective_url"] and result["effective_url"] != url:
        posting = _board_api(result, url)
    if posting:
        result.update(method="ats-api", confidence="high", posting=posting)
        return result

    if page_text and page_text["description_text"]:
        confidence = _confidence(page_text["description_text"])
        result.update(method="page-text", confidence=confidence, posting=page_text)
        if confidence == "medium":
            return result
        result["warnings"].append("page text is short or looks like a login, block, or JavaScript shell")
    result["warnings"].append("no reliable posting text; try a browser tool, then ask the user to paste the posting")
    return result


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("-o", "--output", type=Path, help="Also write the JSON result to this file")
    args = parser.parse_args(argv)

    result = fetch(args.url)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if result["confidence"] in ("medium", "high") else 2


if __name__ == "__main__":
    sys.exit(main())
