# SKILL.md — DevOps Remote Job Scraper

Documentação técnica das habilidades e padrões utilizados neste projeto. Use como referência para manutenção, extensão e onboarding.

---

## 1. Web Scraping com BeautifulSoup

### Quando usar

Para sites que retornam HTML estático (sem JavaScript client-side).

### Padrão adotado

```python
import requests
from bs4 import BeautifulSoup

resp = requests.get(url, headers=HEADERS, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Prefira seletores CSS específicos
items = soup.select("article[class*='job']")

# Fallback com seletores mais genéricos
title = card.select_one("h2, h3, [class*='title']")
```

### Boas práticas

- Sempre definir `timeout` no request (evita travar indefinidamente)
- Usar `select_one()` com múltiplos seletores separados por vírgula como fallback
- Nunca assumir que um elemento existe — sempre checar `if el:` antes de `.text`
- Adicionar `time.sleep(1.0 a 1.5)` entre requests do mesmo domínio

### Sinal de alerta

Se `soup.select(...)` retornar lista vazia, o site provavelmente é SPA (JavaScript). Migrar para `playwright`.

---

## 2. Consumo de APIs e RSS

### API JSON (RemoteOK)

```python
resp = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=20)
data = resp.json()
# RemoteOK: primeiro item é metadata — sempre pular com data[1:]
for item in data[1:]:
    if not isinstance(item, dict):
        continue
```

### RSS Feed (We Work Remotely)

```python
soup = BeautifulSoup(resp.content, "xml")  # parser "xml", não "html.parser"
items = soup.find_all("item")
for item in items:
    title = item.find("title").text
    link = item.find("link").text
```

> **Nota:** RSS é o método mais estável — raramente quebra com atualizações de layout.

---

## 3. Funções Utilitárias

Helpers compartilhados entre todos os scrapers:

```python
def clean_text(text: str) -> str:
    """Normaliza espaços e strips — sempre usar antes de guardar um campo."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())

def contains_exclusion(text: str) -> bool:
    """True se o texto contiver qualquer termo de exclusão (case-insensitive)."""
    text_lower = text.lower()
    return any(term in text_lower for term in CONFIG["exclude_terms"])

def has_relevant_skills(text: str) -> bool:
    """True se o texto contiver ao menos uma skill de must_have_any."""
    text_lower = text.lower()
    return any(skill in text_lower for skill in CONFIG["must_have_any"])
```

---

## 4. Filtragem e Relevância

### Arquitetura de filtros

```
vaga
 └─ contains_exclusion()  →  descarta se tiver "US Only", "clearance", etc.
 └─ is_relevant()
     ├─ keyword no título       →  aceita
     └─ has_relevant_skills()   →  aceita (busca em título + descrição)
```

### Padrão de implementação

```python
def is_relevant(title: str, description: str = "") -> bool:
    combined = f"{title} {description}".lower()
    if contains_exclusion(combined):
        return False
    title_match = any(kw in title.lower() for kw in CONFIG["keywords"])
    return title_match or has_relevant_skills(combined)
```

> **Nota:** `has_relevant_skills` recebe o texto combinado (`título + descrição`) já em lowercase. Não passar só o título.

### Como calibrar

- Se estiver retornando vagas irrelevantes → adicionar termos em `exclude_terms`
- Se estiver perdendo vagas relevantes → adicionar keywords ou skills em `must_have_any`
- Para perfis diferentes (ex: Frontend, Data Engineer) → trocar `keywords` e `must_have_any` inteiramente

---

## 5. Extração de Salário com Regex

```python
import re

def extract_salary(text: str) -> str:
    patterns = [
        r"\$[\d,]+\s*[-–]\s*\$[\d,]+\s*(?:k|K)?(?:/yr|/year)?",
        r"\$[\d,]+\s*(?:k|K)?\s*(?:/yr|/year)?",
        r"USD\s*[\d,]+",
        r"[\d,]+\s*[-–]\s*[\d,]+\s*USD",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "—"
```

**Padrões cobertos:**

- `$80,000 – $120,000/yr`
- `$100k`
- `USD 90000`
- `80,000 – 120,000 USD`

---

## 6. Deduplicação

```python
def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower()[:40], job["company"].lower()[:30])
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique
```

A chave é `(título truncado, empresa truncada)` — evita duplicatas entre fontes sem ser excessivamente restritiva.

---

## 7. Output: CSV e JSON

```python
import pandas as pd
import json

# CSV
df = pd.DataFrame(jobs)
df.to_csv("saida.csv", index=False, encoding="utf-8")

# JSON
with open("saida.json", "w", encoding="utf-8") as f:
    json.dump(jobs, f, ensure_ascii=False, indent=2)
```

`ensure_ascii=False` é obrigatório para preservar caracteres especiais (é, ã, ü, etc.).

---

## 8. Interface de Terminal com Rich

```python
from rich.console import Console
from rich.table import Table
from rich.progress import track

console = Console()

# Tabela formatada
table = Table(title="Vagas", show_lines=True)
table.add_column("Cargo", style="bold cyan", max_width=35)
table.add_column("Salário", style="yellow")
console.print(table)

# Progress bar
for name, scraper in track(scrapers, description="Buscando..."):
    ...

# Log colorido
console.print(f"[green]✅ OK[/green]")
console.print(f"[yellow]⚠ Aviso[/yellow]")
console.print(f"[red]❌ Erro[/red]")
```

---

## 9. Estrutura de Dados — Job Dict

Todo job retornado pelos scrapers segue este schema:

```python
{
    "title":     str,   # Cargo exato como aparece no site
    "company":   str,   # Nome da empresa ("—" se não encontrado)
    "salary":    str,   # Salário formatado ("—" se não disponível)
    "location":  str,   # Ex: "Remote (Worldwide)", "Remote (EU)"
    "url":       str,   # Link direto para a vaga
    "source":    str,   # Nome do site de origem
    "found_at":  str,   # Timestamp: "YYYY-MM-DD HH:MM"
}
```

---

## 10. Tratamento de Erros

Cada scraper usa `try/except` isolado para não interromper os demais:

```python
try:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return jobs
    # ... lógica de scraping
except Exception as e:
    console.print(f"[yellow]NomeSite: {e}[/yellow]")

return jobs  # sempre retorna lista (vazia se falhar)
```

**Nunca** usar `except` genérico sem logar — dificulta debug.

---

## 11. Escalabilidade — Quando Adicionar Playwright

Use `playwright` em vez de `requests + BeautifulSoup` quando:

- `soup.select(seletor)` retorna lista vazia em site que claramente tem vagas
- O HTML retornado contém `<div id="root"></div>` (SPA React/Vue)
- O site usa lazy loading ou infinite scroll

Instalação:

```bash
pip install playwright
playwright install chromium
```

Padrão de uso:

```python
from playwright.sync_api import sync_playwright

def scrape_spa_site() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, "html.parser")
    # ... resto igual ao padrão BeautifulSoup
```

---

## Referências

- [BeautifulSoup Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests Docs](https://requests.readthedocs.io/)
- [Rich Docs](https://rich.readthedocs.io/)
- [RemoteOK API](https://remoteok.com/api)
- [WWR RSS Feeds](https://weworkremotely.com/remote-jobs.rss)
