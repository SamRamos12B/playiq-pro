import streamlit as st
import pandas as pd
import plotly.express as px
from data.loader import filter_data

TEAM_NAMES = {
    "ARI": "Arizona Cardinals",   "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",   "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",  "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",      "DEN": "Denver Broncos",
    "DET": "Detroit Lions",       "GB":  "Green Bay Packers",
    "HOU": "Houston Texans",      "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars","KC":  "Kansas City Chiefs",
    "LAC": "LA Chargers",         "LAR": "LA Rams",
    "LV":  "Las Vegas Raiders",   "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",   "NE":  "New England Patriots",
    "NO":  "New Orleans Saints",  "NYG": "NY Giants",
    "NYJ": "NY Jets",             "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
    "SF":  "San Francisco 49ers", "TB":  "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",    "WAS": "Washington Commanders",
    "LA":  "LA Rams",
}

def render_free_filters(df: pd.DataFrame) -> dict:
    seasons = sorted(df["season"].dropna().unique().astype(int).tolist())

    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])

    with fc1:
        season = st.selectbox("Season", seasons, index=len(seasons)-1)
    with fc2:
        teams  = ["All"] + sorted(df["posteam"].dropna().unique().tolist())
        equipo = st.selectbox("Team", teams, format_func=lambda x: TEAM_NAMES.get(x, x))
    with fc3:
        tipo = st.selectbox("Play type", ["All", "pass", "run"])
    with fc4:
        st.markdown("&nbsp;")
        from services.stripe_service import create_checkout_session
        user = st.session_state.get("user", {})
        checkout_url = create_checkout_session(user["email"], user["id"])
        st.link_button(
            "⭐ Upgrade to Pro",
            checkout_url,
            type="primary",
            use_container_width=True
        )

    return {
        "season":        season,
        "equipo":        equipo,
        "tipo_play":     tipo,
        "teams":         [] if equipo == "All" else [equipo],
        "concepts":      [],
        "coverages":     [],
        "formation":     "All",
        "downs":         [],
        "seasons":       [season],
        "weeks":         [],
        "defteam":       "All",
        "def_formation": "All",
    }


def render_free_dashboard(filtered_df: pd.DataFrame):
    if filtered_df.empty:
        st.warning("No data for the current filters.")
        return

    # ── Métricas ──────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total plays",  f"{len(filtered_df):,}")
    m2.metric("Avg EPA",      f"{filtered_df['epa'].mean():+.3f}")
    m3.metric("Success rate", f"{(filtered_df['epa'] > 0).mean():.1%}")
    m4.metric("Avg yards",    f"{filtered_df['yards_gained'].mean():.1f}")

    st.divider()

    # ── Gráficas ──────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**EPA by week**")
        epa_week = filtered_df.groupby("week")["epa"].mean().reset_index()
        fig_line = px.line(
            epa_week, x="week", y="epa",
            markers=True,
            color_discrete_sequence=["#00d4ff"],
        )
        fig_line.add_hline(y=0, line_dash="dash",
                           line_color="rgba(255,255,255,0.3)")
        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title="Week", yaxis_title="Avg EPA",
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col_right:
        st.markdown("**Play type distribution**")
        dist = filtered_df["play_type"].value_counts().reset_index()
        dist.columns = ["Type", "Count"]
        fig_pie = px.pie(
            dist, values="Count", names="Type",
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Preview Pro ───────────────────────────────────────
    if "concept" in filtered_df.columns:
        st.divider()
        st.markdown("**Top concepts by EPA** *(Pro preview)*")
        top = (
            filtered_df.groupby("concept")["epa"]
            .mean().nlargest(5).reset_index()
        )
        top.columns = ["Concept", "Avg EPA"]
        fig_bar = px.bar(
            top, x="Avg EPA", y="Concept", orientation="h",
            color="Avg EPA", color_continuous_scale="RdYlGn",
            height=200,
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig_bar, use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("🔒 Concept vs Coverage heatmap, play diagrams y más en Pro")
