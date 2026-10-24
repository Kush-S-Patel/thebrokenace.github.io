"""Render untailored Kush_Patel_Resume.pdf from AutoTailor YAML (no OpenAI)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pdfkit
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


def _wkhtmltopdf_config() -> pdfkit.configuration:
    candidates = [
        os.environ.get("WKHTMLTOPDF_PATH", "").strip(),
        shutil.which("wkhtmltopdf") or "",
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        "/usr/bin/wkhtmltopdf",
        "/usr/local/bin/wkhtmltopdf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return pdfkit.configuration(wkhtmltopdf=path)
    # Let pdfkit try PATH discovery
    return pdfkit.configuration()


def render_resume_pdf(
    resume_yml: Path,
    template_dir: Path,
    *,
    target_title: str,
    html_out: Path,
    pdf_out: Path,
) -> Path:
    with resume_yml.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["target_title"] = target_title

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("resume.html.j2").render(**data)

    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(html, encoding="utf-8")

    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    options = {
        "page-size": "Letter",
        "margin-top": "0.4in",
        "margin-right": "0.5in",
        "margin-bottom": "0.4in",
        "margin-left": "0.5in",
        "encoding": "UTF-8",
        "quiet": "",
    }
    pdfkit.from_file(
        str(html_out),
        str(pdf_out),
        configuration=_wkhtmltopdf_config(),
        options=options,
    )
    return pdf_out
