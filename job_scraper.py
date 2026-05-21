#!/usr/bin/env python3
"""
DevOps Remote Job Scraper
Busca vagas remotas internacionais em múltiplos agregadores.
Sites: Himalayas, We Work Remotely, RemoteOK, Jobspresso, NoDesk
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

# ─────────────────────────────────────────────
# CONFIGURAÇÃO — edite aqui conforme necessário
# ─────────────────────────────────────────────
CONFIG = {
    "keywords": [
        "devops",
        "platform engineer",
        "cloud engineer",
        "site reliability engineer",
        "sre",
        "infrastructure engineer",
    ],
    "must_have_any": [          # vaga precisa ter pelo menos um desses
        "terraform", "ansible", "kubernetes", "openshift",
        "aws", "azure", "ci/cd", "iac", "remote",
    ],
    "exclude_terms": [          # vagas com esses termos são descartadas
        "us only", "us citizens", "clearance", "on-site", "onsite",
        "must be located in", "security clearance",
    ],
    "min_salary_usd": 0,        # 0 = sem filtro; ex: 80000 para filtrar abaixo de $80k
    "output_csv": "vagas_devops_remote.csv",
    "output_json": "vagas_devops_remote.json",
    "output_html": "vagas_devops_remote.html",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ─────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def contains_exclusion(text: str) -> bool:
    text_lower = text.lower()
    return any(term in text_lower for term in CONFIG["exclude_terms"])


def has_relevant_skills(text: str) -> bool:
    text_lower = text.lower()
    return any(skill in text_lower for skill in CONFIG["must_have_any"])


def is_relevant(title: str, description: str = "") -> bool:
    combined = f"{title} {description}".lower()
    if contains_exclusion(combined):
        return False
    title_match = any(kw in title.lower() for kw in CONFIG["keywords"])
    return title_match or has_relevant_skills(combined)


def extract_salary(text: str) -> str:
    patterns = [
        r"\$[\d,]+\s*[-–]\s*\$[\d,]+\s*(?:k|K)?(?:/yr|/year|/ano)?",
        r"\$[\d,]+\s*(?:k|K)?\s*(?:/yr|/year)?",
        r"USD\s*[\d,]+",
        r"[\d,]+\s*[-–]\s*[\d,]+\s*USD",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "—"


# ─────────────────────────────────────────────
# SCRAPERS
# ─────────────────────────────────────────────

def scrape_himalayas() -> list[dict]:
    jobs = []
    base = "https://himalayas.app"
    search_terms = ["devops", "platform-engineer", "sre", "cloud-engineer"]

    for term in search_terms:
        url = f"{base}/jobs/{term}/remote"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select("a[href*='/jobs/companies']") or soup.select("div[class*='job'] a")

            for card in cards:
                title_el = card.select_one("h2, h3, [class*='title']")
                company_el = card.select_one("[class*='company'], [class*='employer']")
                salary_el = card.select_one("[class*='salary'], [class*='compensation']")
                location_el = card.select_one("[class*='location']")

                title = clean_text(title_el.text) if title_el else clean_text(card.text[:80])
                if not title or len(title) < 4:
                    continue

                href = card.get("href", "")
                job = {
                    "title": title,
                    "company": clean_text(company_el.text) if company_el else "—",
                    "salary": clean_text(salary_el.text) if salary_el else "—",
                    "location": clean_text(location_el.text) if location_el else "Remote",
                    "url": base + href if href.startswith("/") else href or url,
                    "source": "Himalayas",
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }

                if is_relevant(job["title"]):
                    jobs.append(job)

            time.sleep(1.5)
        except Exception as e:
            console.print(f"[yellow]Himalayas ({term}): {e}[/yellow]")

    return jobs


def scrape_weworkremotely() -> list[dict]:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    ]

    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.content, "xml")

            for item in soup.find_all("item"):
                title_tag = item.find("title")
                link_tag = item.find("link")
                desc_tag = item.find("description")
                company_tag = item.find("company") or item.find("author")

                title = clean_text(title_tag.text) if title_tag else ""
                link = clean_text(link_tag.text) if link_tag else ""
                raw_desc = clean_text(desc_tag.text) if desc_tag else ""
                description = re.sub(r"<[^>]+>", " ", raw_desc)
                company = clean_text(company_tag.text) if company_tag else "—"

                job = {
                    "title": title,
                    "company": company,
                    "salary": extract_salary(description),
                    "location": "Remote (Worldwide)" if "worldwide" in description.lower() else "Remote",
                    "url": link,
                    "source": "WeWorkRemotely",
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }

                if is_relevant(job["title"], description):
                    jobs.append(job)

            time.sleep(1)
        except Exception as e:
            console.print(f"[yellow]WeWorkRemotely: {e}[/yellow]")

    return jobs


def scrape_remoteok() -> list[dict]:
    jobs = []
    tags_filter = {"devops", "cloud", "aws", "kubernetes", "terraform",
                   "infrastructure", "sre", "platform", "ansible", "openshift"}

    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=20,
        )
        if resp.status_code != 200:
            return jobs

        for item in resp.json()[1:]:  # primeiro item é metadata
            if not isinstance(item, dict):
                continue

            title = clean_text(item.get("position", ""))
            description = clean_text(item.get("description", ""))
            item_tags = {t.lower() for t in item.get("tags", [])}

            if not (item_tags & tags_filter or is_relevant(title, description)):
                continue
            if contains_exclusion(f"{title} {description}"):
                continue

            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")

            if CONFIG["min_salary_usd"] > 0 and salary_min and salary_min < CONFIG["min_salary_usd"]:
                continue

            if salary_min and salary_max:
                salary = f"${salary_min:,} – ${salary_max:,}/yr"
            elif salary_min:
                salary = f"${salary_min:,}+/yr"
            else:
                salary = "—"

            jobs.append({
                "title": title,
                "company": clean_text(item.get("company", "—")),
                "salary": salary,
                "location": "Remote (Worldwide)",
                "url": item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
                "source": "RemoteOK",
                "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

        time.sleep(1)
    except Exception as e:
        console.print(f"[yellow]RemoteOK: {e}[/yellow]")

    return jobs


def scrape_jobspresso() -> list[dict]:
    jobs = []
    url = "https://jobspresso.co/remote-work/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select("li[class*='job_listing'], article[class*='job']"):
            title_el = item.select_one(".position, h3, [class*='title']")
            company_el = item.select_one(".company, [class*='company']")
            link_el = item.select_one("a")

            title = clean_text(title_el.text) if title_el else ""
            if not title:
                continue

            job = {
                "title": title,
                "company": clean_text(company_el.text) if company_el else "—",
                "salary": "—",
                "location": "Remote",
                "url": link_el["href"] if link_el and link_el.get("href") else url,
                "source": "Jobspresso",
                "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

            if is_relevant(job["title"]):
                jobs.append(job)

        time.sleep(1)
    except Exception as e:
        console.print(f"[yellow]Jobspresso: {e}[/yellow]")

    return jobs


def scrape_nodesk() -> list[dict]:
    jobs = []
    for term in ["devops", "platform-engineer", "infrastructure"]:
        url = f"https://nodesk.co/remote-jobs/{term}/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            for card in soup.select("article, [class*='job-card'], [class*='listing']"):
                title_el = card.select_one("h2, h3, [class*='title']")
                company_el = card.select_one("[class*='company']")
                link_el = card.select_one("a[href]")

                title = clean_text(title_el.text) if title_el else ""
                if not title or len(title) < 5:
                    continue

                job = {
                    "title": title,
                    "company": clean_text(company_el.text) if company_el else "—",
                    "salary": "—",
                    "location": "Remote",
                    "url": link_el["href"] if link_el else url,
                    "source": "NoDesk",
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                if is_relevant(job["title"]):
                    jobs.append(job)

            time.sleep(1.2)
        except Exception as e:
            console.print(f"[yellow]NoDesk ({term}): {e}[/yellow]")

    return jobs


# ─────────────────────────────────────────────
# DEDUPLICAÇÃO
# ─────────────────────────────────────────────

def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower()[:40], job["company"].lower()[:30])
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ─────────────────────────────────────────────
# SAÍDA
# ─────────────────────────────────────────────

def print_table(jobs: list[dict]) -> None:
    table = Table(
        title=f"Vagas DevOps Remote — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Cargo", style="bold cyan", max_width=35)
    table.add_column("Empresa", style="green", max_width=20)
    table.add_column("Salário", style="yellow", max_width=22)
    table.add_column("Fonte", style="magenta", max_width=14)
    table.add_column("URL", style="blue", max_width=45, no_wrap=True)

    for i, job in enumerate(jobs, 1):
        table.add_row(
            str(i),
            job["title"][:35],
            job["company"][:20],
            job["salary"],
            job["source"],
            job["url"][:45],
        )
    console.print(table)


_SOURCE_COLORS = {
    "RemoteOK":       "#4f46e5",
    "WeWorkRemotely": "#16a34a",
    "Himalayas":      "#7c3aed",
    "Jobspresso":     "#ea580c",
    "NoDesk":         "#0891b2",
}


def export_html(jobs: list[dict]) -> None:
    import html as html_lib

    def badge(source: str) -> str:
        color = _SOURCE_COLORS.get(source, "#6b7280")
        return (
            f'<span class="badge" style="background:{color}">'
            f'{html_lib.escape(source)}</span>'
        )

    def salary_html(salary: str) -> str:
        if salary and salary != "—":
            return f'<span class="salary">{html_lib.escape(salary)}</span>'
        return '<span class="salary no-salary">—</span>'

    cards_html = ""
    sources = sorted({j["source"] for j in jobs})

    for job in jobs:
        src = html_lib.escape(job["source"])
        cards_html += f"""
        <article class="card" data-source="{src}">
          <div class="card-header">
            {badge(job["source"])}
            <span class="location">{html_lib.escape(job.get("location","Remote"))}</span>
          </div>
          <h2 class="title">{html_lib.escape(job["title"])}</h2>
          <p class="company">{html_lib.escape(job["company"])}</p>
          {salary_html(job["salary"])}
          <div class="card-footer">
            <span class="found-at">{html_lib.escape(job["found_at"])}</span>
            <a class="btn" href="{html_lib.escape(job['url'])}" target="_blank" rel="noopener">
              Ver vaga →
            </a>
          </div>
        </article>"""

    filter_buttons = '<button class="filter-btn active" data-filter="all">Todas</button>'
    for src in sources:
        color = _SOURCE_COLORS.get(src, "#6b7280")
        count = sum(1 for j in jobs if j["source"] == src)
        filter_buttons += (
            f'<button class="filter-btn" data-filter="{html_lib.escape(src)}" '
            f'style="--c:{color}">{html_lib.escape(src)} '
            f'<span class="cnt">{count}</span></button>'
        )

    total = len(jobs)
    with_salary = sum(1 for j in jobs if j["salary"] != "—")
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DevOps Remote Jobs — {generated_at}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #0f172a; --surface: #1e293b; --border: #334155;
    --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8;
  }}
  body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
          min-height: 100vh; padding: 2rem 1rem; }}
  header {{ max-width: 1200px; margin: 0 auto 2rem; }}
  h1 {{ font-size: 1.75rem; font-weight: 700; color: var(--accent); margin-bottom: .5rem; }}
  .meta {{ color: var(--muted); font-size: .9rem; margin-bottom: 1.5rem; }}
  .meta strong {{ color: var(--text); }}
  .controls {{ display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }}
  #search {{
    flex: 1; min-width: 200px; padding: .5rem .75rem;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: .95rem; outline: none;
  }}
  #search:focus {{ border-color: var(--accent); }}
  .filters {{ display: flex; flex-wrap: wrap; gap: .5rem; }}
  .filter-btn {{
    padding: .35rem .8rem; border-radius: 99px; border: 1px solid var(--border);
    background: var(--surface); color: var(--muted); cursor: pointer;
    font-size: .85rem; transition: all .15s;
  }}
  .filter-btn:hover {{ border-color: var(--c, var(--accent)); color: var(--text); }}
  .filter-btn.active {{ background: var(--c, var(--accent)); border-color: var(--c, var(--accent));
                        color: #fff; }}
  .filter-btn[data-filter="all"] {{ --c: #38bdf8; }}
  .cnt {{ opacity: .7; font-size: .8em; }}
  #count-info {{ color: var(--muted); font-size: .85rem; margin: 1rem 0 .5rem;
                 max-width: 1200px; margin-left: auto; margin-right: auto; }}
  .grid {{
    max-width: 1200px; margin: 0 auto;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem;
  }}
  .card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column; gap: .6rem;
    transition: border-color .15s, transform .15s;
  }}
  .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .card.hidden {{ display: none; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: center; }}
  .badge {{
    font-size: .75rem; font-weight: 600; padding: .2rem .6rem;
    border-radius: 99px; color: #fff; letter-spacing: .02em;
  }}
  .location {{ font-size: .78rem; color: var(--muted); }}
  .title {{ font-size: 1rem; font-weight: 600; line-height: 1.35; color: var(--text); }}
  .company {{ font-size: .88rem; color: var(--muted); }}
  .salary {{ font-size: .9rem; font-weight: 600; color: #4ade80; }}
  .no-salary {{ color: var(--muted); font-weight: 400; }}
  .card-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: auto; }}
  .found-at {{ font-size: .75rem; color: var(--muted); }}
  .btn {{
    padding: .35rem .9rem; background: var(--accent); color: #0f172a;
    border-radius: 8px; text-decoration: none; font-size: .85rem; font-weight: 600;
    transition: opacity .15s;
  }}
  .btn:hover {{ opacity: .85; }}
  .empty {{ text-align: center; color: var(--muted); padding: 4rem; grid-column: 1/-1; }}
</style>
</head>
<body>
<header>
  <h1>DevOps Remote Jobs</h1>
  <p class="meta">
    Gerado em <strong>{generated_at}</strong> &nbsp;·&nbsp;
    <strong>{total}</strong> vagas &nbsp;·&nbsp;
    <strong>{with_salary}</strong> com salário
  </p>
  <div class="controls">
    <input id="search" type="search" placeholder="Buscar cargo, empresa..." autocomplete="off">
    <div class="filters">{filter_buttons}</div>
  </div>
</header>
<p id="count-info"></p>
<main class="grid">{cards_html}
  <p class="empty" id="empty-msg" style="display:none">Nenhuma vaga encontrada.</p>
</main>
<script>
  const cards = Array.from(document.querySelectorAll('.card'));
  const search = document.getElementById('search');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const countInfo = document.getElementById('count-info');
  const emptyMsg = document.getElementById('empty-msg');
  let activeFilter = 'all';

  function update() {{
    const q = search.value.toLowerCase();
    let visible = 0;
    cards.forEach(c => {{
      const matchFilter = activeFilter === 'all' || c.dataset.source === activeFilter;
      const matchSearch = !q || c.textContent.toLowerCase().includes(q);
      const show = matchFilter && matchSearch;
      c.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    countInfo.textContent = visible + ' vaga' + (visible !== 1 ? 's' : '') + ' exibida' + (visible !== 1 ? 's' : '');
    emptyMsg.style.display = visible === 0 ? 'block' : 'none';
  }}

  filterBtns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      update();
    }});
  }});

  search.addEventListener('input', update);
  update();
</script>
</body>
</html>"""

    with open(CONFIG["output_html"], "w", encoding="utf-8") as f:
        f.write(html_content)
    console.print(f"[green]HTML salvo: {CONFIG['output_html']}[/green]")


def save_outputs(jobs: list[dict]) -> None:
    pd.DataFrame(jobs).to_csv(CONFIG["output_csv"], index=False, encoding="utf-8")
    console.print(f"[green]CSV salvo: {CONFIG['output_csv']}[/green]")

    with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    console.print(f"[green]JSON salvo: {CONFIG['output_json']}[/green]")

    export_html(jobs)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    console.rule("[bold blue]DevOps Remote Job Scraper[/bold blue]")
    console.print(f"Keywords: [cyan]{', '.join(CONFIG['keywords'])}[/cyan]")
    console.print(f"Must-have skills: [yellow]{', '.join(CONFIG['must_have_any'])}[/yellow]")
    console.print()

    scrapers = [
        ("Himalayas", scrape_himalayas),
        ("We Work Remotely", scrape_weworkremotely),
        ("RemoteOK", scrape_remoteok),
        ("Jobspresso", scrape_jobspresso),
        ("NoDesk", scrape_nodesk),
    ]

    all_jobs: list[dict] = []
    for name, scraper in scrapers:
        console.print(f"  → {name}...", end=" ")
        results = scraper()
        console.print(f"[green]{len(results)} vagas[/green]")
        all_jobs.extend(results)

    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: (j["salary"] == "—", j["source"]))

    console.print()
    console.print(f"[bold]Total de vagas únicas: {len(all_jobs)}[/bold]")
    console.print()

    if all_jobs:
        print_table(all_jobs)
        save_outputs(all_jobs)
    else:
        console.print("[red]Nenhuma vaga encontrada. Tente novamente mais tarde.[/red]")


if __name__ == "__main__":
    main()
