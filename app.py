#!/usr/bin/env python3
"""
Remote Job Scraper — Interface Streamlit
Executa: streamlit run app.py
"""

import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from job_scraper import CONFIG as DEFAULT_CONFIG, run_scraper, save_outputs

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Remote Job Scraper",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

ALL_KEYWORDS = [
    "devops", "platform engineer", "cloud engineer",
    "site reliability engineer", "sre", "infrastructure engineer",
    "devsecops", "mlops", "data engineer", "backend engineer",
    "systems engineer", "network engineer", "cloud architect",
    "software engineer", "backend engineer", "frontend engineer",
    "fullstack engineer"
]

ALL_SKILLS = [
    # DevOps / Cloud / Infra
    "terraform", "ansible", "kubernetes", "openshift",
    "aws", "azure", "gcp", "ci/cd", "iac",
    "docker", "helm", "argocd", "github actions", "jenkins",
    "linux", "prometheus", "grafana", "vault", "consul",
    "pulumi", "crossplane", "datadog", "newrelic",
    # Backend
    "python", "golang", "java", "kotlin", "rust", "scala",
    "ruby", "php", "elixir", "dotnet", "c#",
    "django", "flask", "fastapi", "spring boot", "rails",
    "laravel", "phoenix", "grpc", "graphql", "rest api",
    "kafka", "rabbitmq", "redis", "postgresql", "mysql", "mongodb",
    # Frontend
    "javascript", "typescript", "react", "vue", "angular",
    "nextjs", "nuxtjs", "svelte", "nodejs",
    "tailwind", "webpack", "vite",
]

ALL_EXCLUDE = [
    "us only", "us citizens", "clearance", "on-site", "onsite",
    "must be located in", "security clearance",
    "eu only", "uk only", "no remote", "hybrid",
    "visa sponsorship not available",
]

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Configuração")

    # --- Keywords ---
    st.subheader("Cargos buscados")
    keywords = st.multiselect(
        "Selecione os títulos de cargo",
        options=ALL_KEYWORDS,
        default=DEFAULT_CONFIG["keywords"],
        label_visibility="collapsed",
    )
    custom_kw = st.text_input("Adicionar cargo personalizado", placeholder="ex: cloud native engineer")
    if custom_kw:
        kw_lower = custom_kw.strip().lower()
        if kw_lower not in [k.lower() for k in keywords]:
            keywords = keywords + [kw_lower]
        st.caption(f"Adicionado: **{kw_lower}**")

    st.divider()

    # --- Skills ---
    st.subheader("Tecnologias (pelo menos uma)")
    skills = st.multiselect(
        "A vaga deve mencionar ao menos uma",
        options=ALL_SKILLS,
        default=DEFAULT_CONFIG["must_have_any"],
        label_visibility="collapsed",
    )
    custom_skill = st.text_input("Adicionar tecnologia", placeholder="ex: crossplane")
    if custom_skill:
        sk_lower = custom_skill.strip().lower()
        if sk_lower not in [s.lower() for s in skills]:
            skills = skills + [sk_lower]
        st.caption(f"Adicionado: **{sk_lower}**")

    st.divider()

    # --- Exclude terms ---
    st.subheader("Termos a excluir")
    exclude = st.multiselect(
        "Vagas com esses termos são descartadas",
        options=ALL_EXCLUDE,
        default=DEFAULT_CONFIG["exclude_terms"],
        label_visibility="collapsed",
    )

    st.divider()

    # --- Salary + Currency ---
    st.subheader("Salário mínimo")
    col_val, col_cur = st.columns([3, 2])
    min_salary = col_val.number_input(
        "Valor",
        min_value=0,
        value=0,
        step=5000,
        label_visibility="collapsed",
    )
    currency = col_cur.selectbox(
        "Moeda",
        options=list(CURRENCY_SYMBOLS.keys()),
        label_visibility="collapsed",
    )
    sym = CURRENCY_SYMBOLS[currency]
    if min_salary > 0:
        st.caption(
            f"Filtro: ≥ {sym}{min_salary:,} {currency}  \n"
            "⚠️ Aplicado simbolicamente — sem conversão de câmbio. "
            "Apenas vagas com salário estruturado (RemoteOK) são filtradas."
        )
    else:
        st.caption("Sem filtro de salário mínimo.")

    st.divider()

    # --- Run button ---
    run_disabled = not keywords and not skills
    run_btn = st.button(
        "🔍 Buscar Vagas",
        type="primary",
        use_container_width=True,
        disabled=run_disabled,
    )
    if run_disabled:
        st.warning("Adicione pelo menos um cargo ou tecnologia.")

# ─────────────────────────────────────────────
# CONTEÚDO PRINCIPAL
# ─────────────────────────────────────────────

st.title("DevOps Remote Job Scraper")
st.caption("Busca vagas remotas em Himalayas, We Work Remotely, RemoteOK, Jobspresso e NoDesk.")

# ─── Execução do scraper ───
if run_btn:
    config = {
        "keywords": keywords,
        "must_have_any": skills,
        "exclude_terms": exclude,
        "min_salary_usd": min_salary,
        "output_csv": DEFAULT_CONFIG["output_csv"],
        "output_json": DEFAULT_CONFIG["output_json"],
        "output_html": DEFAULT_CONFIG["output_html"],
    }

    with st.status("Buscando vagas...", expanded=True) as status:
        results_by_source: dict[str, int] = {}

        def on_progress(source_name: str, count: int) -> None:
            icon = "✅" if count > 0 else "⬜"
            st.write(f"{icon} **{source_name}** — {count} vaga{'s' if count != 1 else ''} encontrada{'s' if count != 1 else ''}")
            results_by_source[source_name] = count

        jobs = run_scraper(config, progress_callback=on_progress)
        save_outputs(jobs)

        label = f"Concluído — {len(jobs)} vaga{'s' if len(jobs) != 1 else ''} única{'s' if len(jobs) != 1 else ''} encontrada{'s' if len(jobs) != 1 else ''}."
        status.update(label=label, state="complete", expanded=False)

    st.session_state.jobs = jobs
    st.session_state.last_run = datetime.now().strftime("%d/%m/%Y %H:%M")

# ─── Exibição dos resultados ───
if st.session_state.jobs:
    jobs = st.session_state.jobs
    last_run = st.session_state.last_run

    if last_run:
        st.caption(f"Última busca: {last_run}")

    # Métricas
    with_salary = sum(1 for j in jobs if j["salary"] != "—")
    sources = sorted({j["source"] for j in jobs})

    m1, m2, m3 = st.columns(3)
    m1.metric("Total de vagas", len(jobs))
    m2.metric("Com salário informado", with_salary)
    m3.metric("Fontes consultadas", len(sources))

    st.divider()

    # Filtro por fonte
    source_filter = st.multiselect(
        "Filtrar por fonte",
        options=sources,
        default=sources,
    )
    filtered = [j for j in jobs if j["source"] in source_filter]

    if filtered:
        df = pd.DataFrame(filtered)[
            ["title", "company", "salary", "location", "source", "url", "found_at"]
        ]

        st.dataframe(
            df,
            column_config={
                "title":    st.column_config.TextColumn("Cargo"),
                "company":  st.column_config.TextColumn("Empresa"),
                "salary":   st.column_config.TextColumn("Salário"),
                "location": st.column_config.TextColumn("Localização"),
                "source":   st.column_config.TextColumn("Fonte"),
                "url":      st.column_config.LinkColumn("Link", display_text="Ver vaga →"),
                "found_at": st.column_config.TextColumn("Encontrado em"),
            },
            use_container_width=True,
            hide_index=True,
            height=min(400, 56 + len(filtered) * 35),
        )

        st.divider()
        st.subheader("Downloads")
        dl1, dl2, dl3 = st.columns(3)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        dl1.download_button(
            "⬇️ CSV",
            data=csv_bytes,
            file_name="vagas_devops_remote.csv",
            mime="text/csv",
            use_container_width=True,
        )

        json_bytes = json.dumps(filtered, ensure_ascii=False, indent=2).encode("utf-8")
        dl2.download_button(
            "⬇️ JSON",
            data=json_bytes,
            file_name="vagas_devops_remote.json",
            mime="application/json",
            use_container_width=True,
        )

        html_path = DEFAULT_CONFIG.get("output_html", "vagas_devops_remote.html")
        if os.path.exists(html_path):
            with open(html_path, "rb") as f:
                html_bytes = f.read()
            dl3.download_button(
                "⬇️ HTML",
                data=html_bytes,
                file_name="vagas_devops_remote.html",
                mime="text/html",
                use_container_width=True,
            )
        else:
            dl3.button("⬇️ HTML", disabled=True, use_container_width=True,
                       help="Execute a busca primeiro para gerar o HTML.")
    else:
        st.info("Nenhuma vaga para as fontes selecionadas.")

else:
    st.info(
        "Configure as opções na barra lateral e clique em **🔍 Buscar Vagas** para iniciar.\n\n"
        "Os resultados serão exibidos aqui após a busca."
    )
