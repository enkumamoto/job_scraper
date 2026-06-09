# CLAUDE.md — DevOps Remote Job Scraper

## Visão Geral do Projeto

Scraper de vagas remotas internacionais configurável para qualquer perfil técnico (DevOps, Backend, Frontend, SRE, etc.). Busca em múltiplos agregadores públicos, filtra por relevância técnica e exporta os resultados em CSV, JSON e HTML.

Possui interface gráfica via **Streamlit** (`app.py`) e modo CLI via `job_scraper.py`. O bloco `CONFIG` no topo do script define os parâmetros padrão usados pela CLI; a GUI sobrescreve esses valores em tempo de execução sem alterar o arquivo.

---

## Estrutura do Projeto

```
.
├── job_scraper.py           # Lógica de scraping, filtragem e exportação
├── app.py                   # Interface gráfica Streamlit
├── requirements.txt         # Dependências Python
├── vagas_devops_remote.csv  # Output gerado (após execução)
├── vagas_devops_remote.json # Output gerado (após execução)
├── vagas_devops_remote.html # Output gerado (após execução)
├── CLAUDE.md                # Este arquivo
└── .claude/
    └── SKILLS.md            # Documentação técnica de habilidades do projeto
```

---

## Como Executar

### Pré-requisitos

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Python 3.12 no Ubuntu/Debian** sem venv:
>
> ```bash
> pip3 install --break-system-packages -r requirements.txt
> ```

### Interface gráfica (Streamlit)

```bash
streamlit run app.py
```

Abre `http://localhost:8501` no browser. A GUI permite configurar keywords, tecnologias, termos de exclusão e salário mínimo com moeda (USD/EUR/GBP) sem editar nenhum arquivo.

### Linha de comando

```bash
python job_scraper.py
```

Usa o `CONFIG` fixo no topo do script. Gera `vagas_devops_remote.csv`, `.json` e `.html` no diretório atual.

---

## Configuração (bloco CONFIG)

Edite o bloco `CONFIG` no topo de `job_scraper.py`:

```python
CONFIG = {
    "keywords": [...],        # Títulos de cargo buscados
    "must_have_any": [...],   # Pelo menos 1 skill obrigatória
    "exclude_terms": [...],   # Termos que descartam a vaga
    "min_salary_usd": 0,      # Filtro de salário mínimo (0 = sem filtro)
    "output_csv": "...",      # Nome do arquivo CSV de saída
    "output_json": "...",     # Nome do arquivo JSON de saída
}
```

---

## Fontes de Dados

| Site             | Método           | Notas                            |
| ---------------- | ---------------- | -------------------------------- |
| RemoteOK         | API JSON pública | Retorna salários estruturados    |
| We Work Remotely | RSS feed         | Categoria DevOps/Sysadmin        |
| Himalayas        | HTML scraping    | Remote-only, boa cobertura EU/US |
| Jobspresso       | HTML scraping    | Curated, menor volume            |
| NoDesk           | HTML scraping    | Aggregator genérico              |

---

## Lógica de Filtragem

1. **`is_relevant(title, description)`** — verifica se o título bate com uma keyword OU se o **título** contém uma skill obrigatória; a descrição é usada apenas para exclusão
2. **`contains_exclusion(text)`** — descarta vagas com termos como "US Only", "clearance", "on-site"
3. **`deduplicate(jobs)`** — remove duplicatas por `(title[:40], company[:30])`
4. **Ordenação final** — vagas com salário explícito aparecem primeiro

---

## Convenções de Código

- Funções de scraping seguem o padrão `scrape_<site>() -> list[dict]`
- Cada job é um `dict` com as chaves: `title`, `company`, `salary`, `location`, `url`, `source`, `found_at`
- Erros por site são capturados individualmente com `try/except` — falha em um site não interrompe os outros
- `time.sleep()` entre requests para evitar rate limiting

---

## Como Adicionar um Novo Site

1. Crie uma função `scrape_novosite() -> list[dict]`
2. Use `HEADERS` global para os requests
3. Filtre com `is_relevant()` e `contains_exclusion()`
4. Adicione a tupla `("Nome", scrape_novosite)` na lista `scrapers` dentro de `run_scraper()`
   - A GUI e o CLI usam `run_scraper()` — adicionar em um lugar cobre os dois modos

Exemplo mínimo:

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

## Limitações Conhecidas

- LinkedIn **não** é suportado diretamente (bloqueio ativo de scraping)
- Sites com JavaScript pesado (React/Vue SPA) podem retornar HTML incompleto — nesses casos, considerar `selenium` ou `playwright`
- Seletores CSS podem quebrar se o site atualizar o layout — verificar periodicamente
- RemoteOK pode retornar 403 em alguns IPs; usar proxy se necessário

---

## Próximos Passos Sugeridos

- [ ] Adicionar suporte a `playwright` para sites JS-heavy (ex: Greenhouse, Lever)
- [ ] Implementar modo `--watch` para rodar em intervalos (ex: a cada 6h via cron)
- [ ] Adicionar envio de alerta por e-mail ou Telegram quando novas vagas forem encontradas
- [ ] Criar filtro de senioridade (senior, staff, principal)
- [ ] Adicionar score de relevância por match de skills do perfil
