import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.loader import load_pbp, filter_pbp, get_teams

def render_filters() -> dict:
    """
    Renderiza los filtros en el sidebar y devuelve los valores activos.
    """
    st.sidebar.header("🔧 Filtros")

    season = st.sidebar.selectbox(
        "Temporada",
        [2024, 2023, 2022, 2021],
        index=0
    )

    teams = ["Todos"] + get_teams(season)
    equipo = st.sidebar.selectbox("Equipo", teams)

    lado = st.sidebar.radio(
        "Perspectiva",
        ["Offense", "Defense"],
        horizontal=True
    )

    semanas = st.sidebar.slider("Semanas", 1, 18, (1, 18))

    tipo_play = st.sidebar.selectbox(
        "Tipo de jugada",
        ["Todas", "pass", "run"]
    )

    return {
        "season":    season,
        "equipo":    equipo,
        "lado":      lado,
        "semanas":   semanas,
        "tipo_play": tipo_play
    }

def render_dashboard(filtros: dict) -> pd.DataFrame:
    """
    Renderiza el dashboard principal y devuelve el df filtrado
    para pasárselo al AI Scout.
    """
    # Cargar y filtrar datos
    df_full = load_pbp(filtros["season"])
    df = filter_pbp(
        df_full,
        filtros["equipo"],
        filtros["semanas"],
        filtros["tipo_play"],
        filtros["lado"]
    )

    if df.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        return df

    # ── Métricas principales ─────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total jugadas", f"{len(df):,}")
    with col2:
        epa_avg = round(df["epa"].mean(), 3)
        st.metric("EPA promedio", epa_avg,
                  delta=f"{'↑' if epa_avg > 0 else '↓'}")
    with col3:
        yards_avg = round(df["yards_gained"].mean(), 1)
        st.metric("Yardas / jugada", yards_avg)
    with col4:
        success = round((df["epa"] > 0).mean() * 100, 1)
        st.metric("Success rate", f"{success}%")

    st.divider()

    # ── Gráficas ─────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**EPA por semana**")
        epa_by_week = df.groupby("week")["epa"].mean().reset_index()
        fig = px.line(
            epa_by_week, x="week", y="epa",
            markers=True,
            color_discrete_sequence=["#00d4ff"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(zeroline=True, zerolinecolor="gray"),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("**Distribución de jugadas**")
        play_dist = df["play_type"].value_counts().reset_index()
        play_dist.columns = ["Tipo", "Count"]
        fig2 = px.pie(
            play_dist, values="Count", names="Tipo",
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Top jugadas por EPA ───────────────────────────────
    st.markdown("**Top 10 jugadas por EPA**")
    cols_show = [c for c in [
        "week", "posteam", "play_type", "down",
        "ydstogo", "yards_gained", "epa",
        "passer_player_name", "rusher_player_name"
    ] if c in df.columns]

    st.dataframe(
        df.nlargest(10, "epa")[cols_show],
        use_container_width=True,
        hide_index=True
    )

    return df