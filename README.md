# DevOps Remote Job Scraper

Scraper de vagas remotas internacionais configurável para qualquer perfil técnico (DevOps, Backend, Frontend, SRE, etc.). Busca em múltiplos agregadores públicos, filtra por relevância técnica e exporta os resultados em CSV, JSON e HTML.

Possui **interface gráfica via Streamlit** e também pode ser usado pela linha de comando.

---

## Fontes

| Site             | Método        | Notas                            |
|------------------|---------------|----------------------------------|
| RemoteOK         | API JSON      | Retorna salários estruturados    |
| We Work Remotely | RSS feed      | Categoria DevOps/Sysadmin        |
| Himalayas        | HTML scraping | Remote-only, boa cobertura EU/US |
| Jobspresso       | HTML scraping | Curated, menor volume            |
| NoDesk           | HTML scraping | Aggregator genérico              |

---

## Instalação

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Python 3.12 no Ubuntu/Debian** sem venv — se o pip reclamar de "externally managed environment":
>
> ```bash
> pip3 install --break-system-packages -r requirements.txt
> ```

---

## Uso

### Interface gráfica (recomendado)

```bash
streamlit run app.py
```

O browser abre em `http://localhost:8501`. Na barra lateral você configura:

- **Cargos buscados** — multiselect com opção de adicionar cargos personalizados
- **Tecnologias** — filtro de skills (DevOps, Backend e Frontend)
- **Termos a excluir** — descarta vagas com restrições geográficas ou de visto
- **Salário mínimo** — valor + escolha de moeda (USD, EUR, GBP)

Após a busca, os resultados aparecem em tabela com links clicáveis e botões de download (CSV, JSON, HTML).

### Linha de comando

```bash
python job_scraper.py
```

Usa o bloco `CONFIG` fixo no topo do script e gera três arquivos no diretório atual:

- `vagas_devops_remote.csv`
- `vagas_devops_remote.json`
- `vagas_devops_remote.html` — relatório visual com filtros e busca

---

## Configuração (CLI)

Edite o bloco `CONFIG` no topo de `job_scraper.py`:

```python
CONFIG = {
    "keywords": [
        "devops", "platform engineer", "cloud engineer",
        "site reliability engineer", "sre", "infrastructure engineer",
    ],
    "must_have_any": [          # vaga precisa ter pelo menos um desses
        "terraform", "ansible", "kubernetes", "openshift",
        "aws", "azure", "ci/cd", "iac",
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
```

---

## Lógica de Filtragem

```
vaga
 └─ contains_exclusion()  →  descarta se título ou descrição tiver "US Only", "clearance"...
 └─ is_relevant()
     ├─ keyword no título       →  aceita ("devops", "platform engineer", "sre"...)
     └─ skill no título         →  aceita (terraform, kubernetes, aws...)
```

> **Nota:** a descrição é usada apenas para exclusão, nunca para aceitar uma vaga. Isso evita que vagas de Marketing/RH passem o filtro por mencionarem "aws" ou "kubernetes" no texto da empresa.

Vagas com salário explícito aparecem primeiro na saída. Duplicatas entre fontes são removidas por `(título[:40], empresa[:30])`.

---

## Adicionando uma Nova Fonte

1. Crie `scrape_novosite() -> list[dict]`
2. Use `HEADERS` global para os requests
3. Filtre com `is_relevant()` e `contains_exclusion()`
4. Adicione `("Nome", scrape_novosite)` na lista `scrapers` dentro de `run_scraper()`

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
- Filtro de salário mínimo só se aplica a vagas com valor estruturado (RemoteOK); conversão de moeda é simbólica

---

## Próximos Passos

- [ ] Alerta por e-mail ou Telegram para novas vagas
- [ ] Filtro de senioridade (senior, staff, principal)
- [ ] Score de relevância por match de skills do perfil
