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


def save_outputs(jobs: list[dict]) -> None:
    pd.DataFrame(jobs).to_csv(CONFIG["output_csv"], index=False, encoding="utf-8")
    console.print(f"[green]CSV salvo: {CONFIG['output_csv']}[/green]")

    with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    console.print(f"[green]JSON salvo: {CONFIG['output_json']}[/green]")


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
