# CLAUDE.md — DevOps Remote Job Scraper

## Visão Geral do Projeto

Scraper de vagas remotas internacionais voltado para profissionais de **DevOps / Platform Engineering / SRE**. Busca em múltiplos agregadores públicos, filtra por relevância técnica e exporta os resultados em CSV e JSON.

O projeto foi construído para o perfil de profissional Senior DevOps Engineer, mas é configurável para qualquer perfil técnico via bloco `CONFIG` no topo do script principal.

---

## Estrutura do Projeto

```
.
├── job_scraper.py           # Script principal
├── vagas_devops_remote.csv  # Output gerado (após execução)
├── vagas_devops_remote.json # Output gerado (após execução)
├── CLAUDE.md                # Este arquivo
└── .claude/
    └── SKILLS.md            # Documentação técnica de habilidades do projeto
```

---

## Como Executar

### Pré-requisitos

```bash
pip install requests beautifulsoup4 pandas rich
```

### Rodar

```bash
python job_scraper.py
```

Os arquivos `vagas_devops_remote.csv` e `vagas_devops_remote.json` serão gerados no diretório atual.

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

1. **`is_relevant(title, description)`** — verifica se o título bate com uma keyword OU se a descrição contém uma skill obrigatória
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
4. Adicione a tupla `("Nome", scrape_novosite)` na lista `scrapers` dentro de `main()`

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
