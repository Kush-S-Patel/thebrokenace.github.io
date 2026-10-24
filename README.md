# patelskush.com

Personal website for Kush Patel.

## Content sync

The site is regenerated from:

1. **AutoTailor** `data/kush_patel.yml` — experience, education, projects, skills, certs, products  
2. **`data/site.yml`** — about blurb, interests, awards extras, skill icons, social links  

`index.html` and `Kush_Patel_Resume.pdf` are **generated artifacts**. Edit the YAML sources, not the HTML by hand. Update the profile photo by replacing `img/profile.jpg` when you want.

### Local sync

```powershell
cd "C:\Users\nikup\Repos\Personal Website\thebrokenace.github.io"
pip install -r sync/requirements.txt
python -m sync.sync
# HTML only:
python -m sync.sync --skip-pdf
```

Requires [wkhtmltopdf](https://wkhtmltopdf.org/) for PDF generation (default Windows path: `C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe`). Without it locally, sync falls back to AutoTailor's `output/Blank/Kush_Patel_Blank_Resume.pdf` if present.

### GitHub Actions

Workflow: `.github/workflows/sync-portfolio.yml`

| Trigger | When |
|---------|------|
| `schedule` | Sundays 16:00 UTC |
| `workflow_dispatch` | Manual run in Actions tab |
| `repository_dispatch` (`autotailor-updated`) | AutoTailor YAML/template push |
| `push` | Changes to `sync/`, `templates/`, or `data/site.yml` |

On change it commits `index.html`, `Kush_Patel_Resume.pdf`, and `data/kush_patel.yml` to `main` (GitHub Pages deploys from there).

### Secrets

**On `thebrokenace.github.io`:**

| Secret | Purpose |
|--------|---------|
| `AUTOTAILOR_PAT` | Only if AutoTailor is **private** (PAT with `repo` read). |

**On `AutoTailor`:**

| Secret | Purpose |
|--------|---------|
| `PORTFOLIO_DISPATCH_PAT` | PAT with `repo` scope on the portfolio repo so pushes to `data/kush_patel.yml` trigger sync. |

### AutoTailor notify workflow

`AutoTailor/.github/workflows/notify-portfolio.yml` fires `repository_dispatch` at this repo whenever resume YAML/template changes.
