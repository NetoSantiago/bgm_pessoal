# app.py — "Santiago - Board Games Victory"

import io
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Santiago - Board Games Victory",
    page_icon="🎲",
    layout="wide",
)

st.title("🎲 Santiago - Board Games Victory")
st.caption("Cadastro de jogos, controle de quantidades e geração de créditos — com exportação de relatórios em CSV.")

ARQUIVO_CSV = Path("jogos.csv")
CAMPOS = ["nome", "qtd_ganha", "qtd_ficar", "qtd_credito", "valor_credito"]
DEFAULT_CREDITO = 59.0

def carregar_df() -> pd.DataFrame:
    if ARQUIVO_CSV.exists():
        df = pd.read_csv(ARQUIVO_CSV)
        # Garantir colunas e tipos
        for c in CAMPOS:
            if c not in df.columns:
                df[c] = 0
        df["nome"] = df["nome"].astype(str).str.strip()
        for c in ["qtd_ganha", "qtd_ficar", "qtd_credito"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        df["valor_credito"] = pd.to_numeric(df["valor_credito"], errors="coerce").fillna(DEFAULT_CREDITO).astype(float)
    else:
        df = pd.DataFrame(columns=CAMPOS)
    return recalc_df(df)


def salvar_df(df: pd.DataFrame) -> None:
    df = recalc_df(df.copy())
    df.to_csv(ARQUIVO_CSV, index=False)


def recalc_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["qtd_credito"] = (df["qtd_ganha"] - df["qtd_ficar"]).clip(lower=0)
    df["valor_credito"] = df["valor_credito"].fillna(DEFAULT_CREDITO).replace(0, DEFAULT_CREDITO)
    return df


def upsert_jogo(df: pd.DataFrame, nome: str, qtd_ganha: int | None = None, qtd_ficar: int | None = None, valor_credito: float | None = None) -> pd.DataFrame:
    nome = (nome or "").strip()
    if not nome:
        return df
    mask = df["nome"].str.lower() == nome.lower()
    if not mask.any():
        # novo registro
        df = pd.concat([
            df,
            pd.DataFrame([{ 
                "nome": nome,
                "qtd_ganha": int(qtd_ganha or 0),
                "qtd_ficar": int(qtd_ficar or 0),
                "qtd_credito": 0,  # será recalculado
                "valor_credito": float(valor_credito if valor_credito is not None else DEFAULT_CREDITO),
            }])
        ], ignore_index=True)
    else:
        # atualização
        idx = df.index[mask][0]
        if qtd_ganha is not None:
            df.at[idx, "qtd_ganha"] = int(df.at[idx, "qtd_ganha"]) + int(qtd_ganha)
        if qtd_ficar is not None:
            df.at[idx, "qtd_ficar"] = int(qtd_ficar)
        if valor_credito is not None:
            df.at[idx, "valor_credito"] = float(valor_credito)
    df = recalc_df(df)
    return df


def df_para_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

st.sidebar.header("⚙️ Ações")
with st.sidebar.expander("Importar/Restaurar CSV", expanded=False):
    up = st.file_uploader("Carregar um jogos.csv (substitui o atual)", type=["csv"])
    if up is not None:
        tmp = pd.read_csv(up)
        tmp = recalc_df(tmp)
        salvar_df(tmp)
        st.success("CSV importado e salvo.")

if st.sidebar.button("💾 Forçar salvar agora", use_container_width=True):
    df_atual = carregar_df()
    salvar_df(df_atual)
    st.sidebar.success("Dados salvos em jogos.csv")

t1, t2 = st.tabs(["Cadastrar / Atualizar", "Relatórios e Exportação"]) 

with t1:
    st.subheader("Cadastro e Atualização de Jogos")

    df = carregar_df()

    colA, colB = st.columns([2, 3])
    with colA:
        st.markdown("**Cadastrar novo jogo**")
        with st.form("form_cadastrar", clear_on_submit=True):
            nome_novo = st.text_input("Nome do jogo")
            qtd_ganha_novo = st.number_input("Quantidade ganha (inicial)", min_value=0, step=1, value=0)
            qtd_ficar_novo = st.number_input("Quantidade que quer ficar (inicial)", min_value=0, step=1, value=0)
            valor_credito_novo = st.number_input("Valor do crédito por unidade", min_value=0.0, step=1.0, value=float(DEFAULT_CREDITO))
            ok_cad = st.form_submit_button("➕ Cadastrar")
        if ok_cad:
            df = upsert_jogo(df, nome_novo, qtd_ganha_novo, qtd_ficar_novo, valor_credito_novo)
            salvar_df(df)
            st.success(f"Jogo '{nome_novo}' cadastrado/atualizado.")

    with colB:
        st.markdown("**Atualizar jogo existente**")
        nomes = sorted(df["nome"].dropna().unique().tolist())
        if nomes:
            alvo = st.selectbox("Escolha um jogo", nomes)
            reg = df[df["nome"] == alvo].iloc[0] if alvo else None
            with st.form("form_atualizar"):
                add_ganha = st.number_input("Adicionar à quantidade ganha", min_value=0, step=1, value=0)
                set_ficar = st.number_input("Definir quantidade que quer ficar", min_value=0, step=1, value=int(reg["qtd_ficar"]))
                set_valor = st.number_input("Valor do crédito por unidade", min_value=0.0, step=1.0, value=float(reg["valor_credito"]))
                ok_upd = st.form_submit_button("📝 Atualizar")
            if ok_upd:
                df = upsert_jogo(df, alvo, add_ganha, set_ficar, set_valor)
                salvar_df(df)
                st.success("Jogo atualizado.")
        else:
            st.info("Nenhum jogo cadastrado ainda.")

    st.divider()
    st.markdown("### Visualização rápida (todos)")
    df_view = carregar_df()
    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
    )

with t2:
    df = carregar_df()

    st.subheader("Relatórios")

    # ---- Relatório: Todos ----
    with st.expander("📋 Lista de jogos ganhos (todos os dados)", expanded=True):
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Baixar CSV (todos)",
            data=df_para_csv_bytes(df),
            file_name="export_todos.csv",
            mime="text/csv",
        )

    # ---- Relatório: Quero trazer ----
    with st.expander("🎒 Lista de jogos que quero trazer (sem colunas de crédito)", expanded=False):
        df_trazer = df[df["qtd_ficar"] > 0][["nome", "qtd_ganha", "qtd_ficar"]].copy()
        st.dataframe(df_trazer, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Baixar CSV (quero trazer)",
            data=df_para_csv_bytes(df_trazer),
            file_name="export_quero_trazer.csv",
            mime="text/csv",
        )

    # ---- Relatório: Para crédito ----
    with st.expander("💳 Lista de jogos para gerar crédito", expanded=True):
        df_credito = df[df["qtd_credito"] > 0].copy()
        df_credito["total_credito"] = df_credito["qtd_credito"] * df_credito["valor_credito"]
        cols_ordem = ["nome", "qtd_ganha", "qtd_ficar", "qtd_credito", "valor_credito", "total_credito"]
        df_credito = df_credito[cols_ordem]

        # Total geral de créditos
        total_geral = float(df_credito["total_credito"].sum()) if not df_credito.empty else 0.0
        m1, m2 = st.columns(2)
        m1.metric("Total de créditos disponíveis", f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        m2.write("")

        st.dataframe(df_credito, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Baixar CSV (para crédito)",
            data=df_para_csv_bytes(df_credito),
            file_name="export_para_credito.csv",
            mime="text/csv",
        )

    st.divider()
    st.info(
        "Dica: você pode editar os dados pelo menu 'Cadastrar / Atualizar' e voltar aqui para ver os relatórios formatados e exportar os CSVs."
    )
