#!/usr/bin/env python3
"""
Sync portfolio site from AutoTailor YAML.

Usage:
  python -m sync.sync
  python -m sync.sync --resume-yml path/to/kush_patel.yml --skip-pdf
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from sync.render import load_yaml, render_index
from sync.resume_pdf import render_resume_pdf

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_AUTOTAILOR = Path(r"C:\Users\nikup\Repos\AutoTailor\data\kush_patel.yml")


def resolve_resume_yml(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"Resume YAML not found: {path}")
        return path

    env_path = os.environ.get("AUTOTAILOR_RESUME_YML", "").strip()
    if env_path and Path(env_path).exists():
        return Path(env_path)

    candidates = [
        # CI: AutoTailor checked out into portfolio workspace
        ROOT / "AutoTailor" / "data" / "kush_patel.yml",
        # Local sibling repos
        DEFAULT_LOCAL_AUTOTAILOR,
        ROOT.parent / "AutoTailor" / "data" / "kush_patel.yml",
        # Cached copy inside this repo
        ROOT / "data" / "kush_patel.yml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find AutoTailor data/kush_patel.yml. "
        "Pass --resume-yml or set AUTOTAILOR_RESUME_YML."
    )


def sync_resume_copy(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.read_bytes() == src.read_bytes():
        return False
    shutil.copy2(src, dest)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync portfolio from AutoTailor")
    parser.add_argument("--resume-yml", help="Path to kush_patel.yml")
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument("--skip-html", action="store_true")
    args = parser.parse_args(argv)

    site_yml = ROOT / "data" / "site.yml"
    site = load_yaml(site_yml)
    resume_src = resolve_resume_yml(args.resume_yml)
    resume_dest = ROOT / "data" / "kush_patel.yml"
    template_dir = ROOT / "templates"

    report: dict = {
        "resume_yml_src": str(resume_src),
        "changes": {},
    }

    report["changes"]["resume_yml"] = sync_resume_copy(resume_src, resume_dest)

    if not args.skip_html:
        render_index(
            resume_dest,
            site_yml,
            template_dir,
            ROOT / "index.html",
        )
        report["changes"]["index_html"] = True

    if not args.skip_pdf:
        pdf_out = ROOT / "Kush_Patel_Resume.pdf"
        try:
            render_resume_pdf(
                resume_dest,
                template_dir,
                target_title=site.get("target_title") or "ML Engineer",
                html_out=ROOT / "output" / "portfolio_resume.html",
                pdf_out=pdf_out,
            )
            report["changes"]["resume_pdf"] = True
        except Exception as exc:  # noqa: BLE001 — surface clearly in CI logs
            report["pdf_error"] = str(exc)
            print(f"WARNING: PDF generation failed: {exc}", file=sys.stderr)
            # Local fallback: copy AutoTailor's untailored Blank PDF if present
            blank = resume_src.parents[1] / "output" / "Blank" / "Kush_Patel_Blank_Resume.pdf"
            if blank.exists():
                shutil.copy2(blank, pdf_out)
                report["changes"]["resume_pdf"] = {
                    "fallback": str(blank),
                    "note": "Copied Blank resume; install wkhtmltopdf for fresh renders",
                }
            else:
                report["changes"]["resume_pdf"] = False
                if os.environ.get("SYNC_REQUIRE_PDF", "").lower() in {"1", "true", "yes"}:
                    print(json.dumps(report, indent=2))
                    return 1
    else:
        report["changes"]["resume_pdf"] = {"skipped": True}

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
