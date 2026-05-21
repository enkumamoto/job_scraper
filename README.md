# DevOps Remote Job Scraper

Scraper de vagas remotas internacionais para profissionais de **DevOps / Platform Engineering / SRE**. Busca em múltiplos agregadores públicos, filtra por relevância técnica e exporta os resultados em CSV e JSON.

---

## Fontes

| Site             | Método        | Notas                         |
|------------------|---------------|-------------------------------|
| RemoteOK         | API JSON      | Retorna salários estruturados |
| We Work Remotely | RSS feed      | Categoria DevOps/Sysadmin     |
| Himalayas        | HTML scraping | Remote-only, boa cobertura EU/US |
| Jobspresso       | HTML scraping | Curated, menor volume         |
| NoDesk           | HTML scraping | Aggregator genérico           |

---

## Instalação

```bash
pip install requests beautifulsoup4 pandas rich
```

---

## Uso

```bash
python job_scraper.py
```

Gera dois arquivos no diretório atual:

- `vagas_devops_remote.csv`
- `vagas_devops_remote.json`

---

## Configuração

Edite o bloco `CONFIG` no topo de `job_scraper.py`:

```python
CONFIG = {
    "keywords": [
        "devops", "platform engineer", "cloud engineer",
        "site reliability engineer", "sre", "infrastructure engineer",
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
```

---

## Lógica de Filtragem

```
vaga
 └─ contains_exclusion()  →  descarta ("US Only", "clearance", "on-site"...)
 └─ is_relevant()
     ├─ keyword no título       →  aceita
     └─ skill na descrição      →  aceita (terraform, kubernetes, aws...)
```

Vagas com salário explícito aparecem primeiro na saída. Duplicatas entre fontes são removidas por `(título[:40], empresa[:30])`.

---

## Adicionando uma Nova Fonte

1. Crie `scrape_novosite() -> list[dict]`
2. Use `HEADERS` global para os requests
3. Filtre com `is_relevant()` e `contains_exclusion()`
4. Adicione `("Nome", scrape_novosite)` na lista `scrapers` em `main()`

```python
def scrape_novosite() -> list[dict]:
    jobs = []
    resp = requests.get("https://novosite.com/jobs", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.select(".job-card"):
        title = clean_text(card.select_one("h3").text)
        if not is_relevant(title):
            continue
        jobs.append({
            "title": title,
            "company": "—",
            "salary": "—",
            "location": "Remote",
            "url": card.select_one("a")["href"],
            "source": "NovoSite",
            "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    return jobs
```

---

## Limitações

- **LinkedIn** não é suportado (bloqueio ativo de scraping)
- Sites React/Vue SPA podem retornar HTML incompleto — considerar `playwright` nesses casos
- Seletores CSS podem quebrar com atualizações de layout — verificar periodicamente
- RemoteOK pode retornar 403 em alguns IPs; usar proxy se necessário

---

## Próximos Passos

- [ ] Suporte a `playwright` para sites JS-heavy (Greenhouse, Lever)
- [ ] Modo `--watch` para rodar em intervalos via cron
- [ ] Alerta por e-mail ou Telegram para novas vagas
- [ ] Filtro de senioridade (senior, staff, principal)
- [ ] Score de relevância por match de skills do perfil
