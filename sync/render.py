"""Merge AutoTailor + site YAML and render index.html."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def expand_month(token: str) -> str:
    key = token.strip().lower()
    names = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }
    if key in MONTHS:
        return names[MONTHS[key]]
    return token


def format_date_label(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if text.lower() == "present":
        return "Present"
    if text.lower().startswith("expected"):
        # Expected May 2027 → Graduating May 2027
        rest = re.sub(r"(?i)^expected\s+", "", text)
        parts = rest.split()
        if parts:
            parts[0] = expand_month(parts[0])
        return "Graduating " + " ".join(parts)

    parts = text.replace(",", " ").split()
    if not parts:
        return text
    if parts[0].lower() in MONTHS:
        parts[0] = expand_month(parts[0])
    return " ".join(parts)


def parse_sort_key(start: str | None, end: str | None) -> tuple[int, int, int]:
    """Sort key: present roles first, then by end/start descending."""
    end_text = (end or "").strip().lower()
    is_present = 1 if end_text == "present" or not end_text else 0

    def year_month(s: str | None) -> tuple[int, int]:
        if not s:
            return (0, 0)
        tokens = re.findall(r"[A-Za-z]+|\d{4}", s)
        year = 0
        month = 0
        for t in tokens:
            if t.isdigit() and len(t) == 4:
                year = int(t)
            elif t.lower() in MONTHS:
                month = MONTHS[t.lower()]
        return year, month

    ey, em = year_month(end if end_text != "present" else None)
    sy, sm = year_month(start)
    # Present → use "now"
    if is_present:
        now = datetime.utcnow()
        ey, em = now.year, now.month
    return (is_present, ey, em, sy, sm)


def company_label(job: dict[str, Any]) -> str:
    company = job.get("company") or ""
    division = job.get("division")
    if division:
        return f"{company}: {division}"
    return company


def prepare_experience(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for job in jobs or []:
        item = deepcopy(job)
        item["company_label"] = company_label(item)
        start = format_date_label(item.get("start"))
        end = format_date_label(item.get("end"))
        if start and end:
            item["date_label"] = f"{start} - {end}"
        elif start:
            item["date_label"] = start
        else:
            item["date_label"] = ""
        item["_sort"] = parse_sort_key(item.get("start"), item.get("end"))
        prepared.append(item)
    prepared.sort(key=lambda j: j["_sort"], reverse=True)
    for item in prepared:
        item.pop("_sort", None)
    return prepared


def prepare_education(
    education: list[dict[str, Any]],
    site: dict[str, Any],
) -> list[dict[str, Any]]:
    overrides = site.get("education_overrides") or []
    prepared: list[dict[str, Any]] = []

    for edu in education or []:
        item = deepcopy(edu)
        degree = item.get("degree") or ""
        override = next(
            (o for o in overrides if o.get("match_degree") and o["match_degree"] in degree),
            None,
        )
        if override:
            item["display_degree"] = override.get("display_degree") or degree
            item["taken"] = override.get("taken") or []
            item["currently_taking"] = override.get("currently_taking") or []
            item["coursework"] = None
        else:
            item["display_degree"] = degree
            item["taken"] = item.get("coursework") or []
            item["currently_taking"] = []

        if item.get("expected_graduation"):
            item["date_label"] = format_date_label(item["expected_graduation"])
        elif item.get("end") and not item.get("start"):
            item["date_label"] = f"Graduated {format_date_label(item['end'])}"
        elif item.get("start") and item.get("end"):
            item["date_label"] = (
                f"{format_date_label(item['start'])} - {format_date_label(item['end'])}"
            )
        elif item.get("end"):
            item["date_label"] = f"Graduated {format_date_label(item['end'])}"
        else:
            item["date_label"] = ""
        prepared.append(item)

    for extra in site.get("education_extra") or []:
        item = deepcopy(extra)
        item["display_degree"] = item.get("degree") or ""
        if item.get("gpa"):
            item["display_degree"] = f"GPA: {item['gpa']}"
        item["taken"] = item.get("coursework") or []
        item["currently_taking"] = []
        if item.get("start") and item.get("end"):
            item["date_label"] = (
                f"{format_date_label(item['start'])} - {format_date_label(item['end'])}"
            )
        else:
            item["date_label"] = format_date_label(item.get("end")) or ""
        prepared.append(item)

    return prepared


def prepare_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for proj in projects or []:
        item = deepcopy(proj)
        tech = item.get("tech") or []
        item["subheading"] = ", ".join(tech) if tech else "Project"
        item["date_label"] = item.get("date") or ""
        prepared.append(item)
    return prepared


def prepare_awards(resume: dict[str, Any], site: dict[str, Any]) -> list[str]:
    awards: list[str] = []
    for cert in resume.get("certifications") or []:
        name = cert.get("name") if isinstance(cert, dict) else str(cert)
        year = cert.get("year") if isinstance(cert, dict) else None
        awards.append(f"{name} Certified" if year and "cert" not in name.lower() else (f"{name} ({year})" if year else name))
        # Prefer cleaner CompTIA line
        if isinstance(cert, dict) and "Security+" in (cert.get("name") or ""):
            awards[-1] = "CompTIA Security+ Certified"

    for product in resume.get("products") or []:
        metrics = product.get("metrics") or {}
        if metrics.get("purchases"):
            awards.append(f"Over {metrics['purchases']} Purchases on iOS App Store")
        if metrics.get("impressions"):
            awards.append(f"Over {metrics['impressions']} Impressions on iOS Applications")
        if metrics.get("downloads"):
            awards.append(f"Over {metrics['downloads']} Downloads on Educational Nonprofit iOS App")

    for aff in resume.get("affiliations") or []:
        if "Apple Developer" in aff:
            awards.append("Certified Apple Non-Profit Organization Developer")
        else:
            awards.append(aff)

    for extra in site.get("awards_extra") or []:
        if extra not in awards:
            awards.append(extra)

    # Dedupe while preserving order
    seen = set()
    unique = []
    for a in awards:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique


def build_context(resume: dict[str, Any], site: dict[str, Any]) -> dict[str, Any]:
    personal = resume.get("personal") or {}
    return {
        "personal": personal,
        "linkedin_url": site.get("linkedin_url")
        or personal.get("linkedin")
        or "https://www.linkedin.com/in/kush-patel-053973216/",
        "about": site.get("about") or [],
        "experience": prepare_experience(resume.get("experience") or []),
        "education": prepare_education(resume.get("education") or [], site),
        "projects": prepare_projects(resume.get("projects") or []),
        "skills": resume.get("skills") or {},
        "skill_icons": site.get("skill_icons") or [],
        "interests": site.get("interests") or {},
        "awards": prepare_awards(resume, site),
        "generated_note": "Content synced from AutoTailor",
    }


def render_index(
    resume_yml: Path,
    site_yml: Path,
    template_dir: Path,
    out_html: Path,
) -> Path:
    resume = load_yaml(resume_yml)
    site = load_yaml(site_yml)
    ctx = build_context(resume, site)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    # Interests paragraphs intentionally contain trusted HTML links from site.yml
    html = env.get_template("index.html.j2").render(**ctx)
    out_html.write_text(html, encoding="utf-8")
    return out_html
