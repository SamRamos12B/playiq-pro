import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data.loader import load_data, filter_data
from models.analytics_engine import (
    concept_performance, concept_vs_coverage,
    third_down_analysis, formation_vs_formation
)
from models.play_diagram_engine import draw_play

# ── Constantes ───────────────────────────────────────────────────────────────
DOWN_SUFFIX = {1: "st", 2: "nd", 3: "rd", 4: "th"}
WEEK_LABELS = {
    **{w: f"Week {w}" for w in range(1, 19)},
    19: "🏆 Wild Card",   20: "🏆 Divisional",
    21: "🏆 Conf. Champ", 22: "🏆 Super Bowl",
}
SORT_OPTIONS = {
    "Top EPA":      ("epa",          False),
    "Bottom EPA":   ("epa",          True),
    "Most Yards":   ("yards_gained", False),
    "Fewest Yards": ("yards_gained", True),
}
CONCEPT_COLORS = {
    "Four Verticals": "#3B82F6", "Slant": "#6366F1",
    "Crosser": "#8B5CF6",        "Mesh": "#A855F7",
    "Spacing": "#EC4899",        "Smash": "#F59E0B",
    "Flood": "#10B981",          "Drive": "#14B8A6",
    "Curl Flat": "#06B6D4",      "Stick": "#0EA5E9",
}
COVERAGE_COLORS = {
    "Cover 3": "#EF4444", "Cover 2": "#F97316",
    "Cover 4": "#F59E0B", "Cover 1": "#84CC16",
    "Cover 0": "#22C55E", "Cover 6": "#EAB308",
    "Tampa 2": "#F97316", "Quarters": "#FBBF24",
}
FORMATION_COLORS = {
    "Shotgun": "#10B981",        "Shotgun Spread": "#059669",
    "Singleback": "#0D9488",     "I-Form": "#0891B2",
    "Pistol": "#7C3AED",         "Empty": "#6D28D9",
    "Wildcat": "#BE185D",
}
FILTER_KEYS = [
    "sel_team", "sel_concept", "sel_formation", "sel_downs",
    "sel_defteam", "sel_def_formation", "sel_coverage",
    "sel_seasons", "sel_weeks", "sel_sort",
]
COLUMN_FORMATS = {
    "down": "{:.0f}", "ydstogo": "{:.0f}",
    "yards_gained": "{:.0f}", "avg_yards": "{:.2f}",
}


# ── Helpers ──────────────────────────────────────────────────────────────────
def style_table(df, pct_cols=(), epa_cols=()):
    fmt = {col: f for col, f in COLUMN_FORMATS.items() if col in df.columns}
    for col in pct_cols:
        if col in df.columns:
            fmt[col] = "{:.1%}"
    for col in epa_cols:
        if col in df.columns:
            fmt[col] = "{:+.3f}"
    s = df.style.format(fmt, na_rep="—")
    for col in epa_cols:
        if col in df.columns:
            s = s.background_gradient(subset=[col], cmap="RdYlGn")
    return s


def play_label(i, row):
    team    = row.get("posteam", "?")
    concept = row.get("concept", "?")
    icon    = "🎯" if row.get("play_type") == "pass" else "🏃"
    try:
        down    = int(row["down"])
        ydstogo = int(row["ydstogo"])
        dn = f"{down}{DOWN_SUFFIX.get(down,'th')} & {ydstogo}"
    except (TypeError, ValueError):
        dn = "—"
    yards = row.get("yards_gained")
    epa   = row.get("epa")
    yards_str = f"{int(yards)} yds" if pd.notna(yards) else "—"
    epa_str   = f"{epa:+.2f} EPA" if pd.notna(epa) else "—"
    return f"{i+1}. {icon} {team}  |  {dn}  |  {concept}  |  {yards_str} · {epa_str}"


def find_similar_plays(play, df, n=3):
    concept  = play.get("concept")
    coverage = play.get("coverage")
    down     = int(play.get("down", 1))
    similar  = df[
        (df["concept"]  == concept) &
        (df["coverage"] == coverage) &
        (df["down"]     == down) &
        (df.index       != play.name)
    ].copy()
    if len(similar) < n:
        similar = df[
            (df["concept"] == concept) &
            (df["down"]    == down) &
            (df.index      != play.name)
        ].copy()
    return similar.nlargest(n, "epa")


def add_trend_column(perf_df, full_df, window_weeks):
    max_week   = full_df["week"].max()
    cut_recent = max_week - window_weeks + 1
    cut_prior  = max_week - (window_weeks * 2) + 1
    concept_col = perf_df["concept"] if "concept" in perf_df.columns else perf_df.index
    rows = []
    for concept in concept_col:
        cdf    = full_df[full_df["concept"] == concept]
        recent = cdf[cdf["week"] >= cut_recent]["epa"].mean()
        prior  = cdf[(cdf["week"] >= cut_prior) & (cdf["week"] < cut_recent)]["epa"].mean()
        delta  = (recent - prior) if pd.notna(recent) and pd.notna(prior) else 0.0
        weeks  = sorted(cdf["week"].unique())[-window_weeks:]
        spark  = [round(cdf[cdf["week"] == w]["epa"].mean(), 3) for w in weeks]
        badge  = "🔥 Hot" if delta > 0.10 else ("❄️ Cooling" if delta < -0.10 else "→ Stable")
        rows.append({"concept": concept, "trend_badge": badge,
                     "trend_delta": round(delta, 3), "spark": spark})
    trend_df = pd.DataFrame(rows).set_index("concept")
    if "concept" in perf_df.columns:
        return perf_df.join(trend_df, on="concept")
    return perf_df.join(trend_df)


# ── Filtros ───────────────────────────────────────────────────────────────────
def render_filters(df: pd.DataFrame) -> dict:
    available_seasons = sorted(df["season"].dropna().unique().astype(int).tolist())
    available_weeks   = sorted(df["week"].dropna().unique().astype(int).tolist())
    week_options      = [WEEK_LABELS.get(w, f"Week {w}") for w in available_weeks]

    with st.container():
        fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 2, 2, 1])
        with fc1:
            sel_team = st.multiselect(
                "Team", sorted(df["posteam"].dropna().unique().tolist()),
                default=[], key="sel_team")
        with fc2:
            sel_downs = st.multiselect("Down", [1,2,3,4], default=[], key="sel_downs")
        with fc3:
            sel_concept = st.multiselect(
                "Concept", sorted(df["concept"].dropna().unique().tolist()),
                default=[], key="sel_concept")
        with fc4:
            sel_coverage = st.multiselect(
                "Coverage", sorted(df["coverage"].dropna().unique().tolist()),
                default=[], key="sel_coverage")
        with fc5:
            st.write("")
            if st.button("↺ Reset", use_container_width=True):
                for k in FILTER_KEYS:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    with st.expander("⚙ More filters", expanded=False):
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            sel_defteam = st.selectbox(
                "Opponent", ["All"] + sorted(df["defteam"].dropna().unique().tolist()),
                key="sel_defteam")
            sel_def_formation = st.selectbox(
                "Defensive Formation",
                ["All"] + sorted(df["def_formation"].dropna().unique().tolist()),
                key="sel_def_formation")
        with mc2:
            sel_formation = st.selectbox(
                "Formation",
                ["All"] + sorted(df["formation_label"].dropna().unique().tolist()),
                key="sel_formation")
        with mc3:
            sel_seasons = st.multiselect(
                "Season", available_seasons,
                default=available_seasons, key="sel_seasons")
            sel_week_labels = st.multiselect(
                "Week", week_options, default=[], key="sel_weeks")

    label_to_week = {v: k for k, v in WEEK_LABELS.items()}
    sel_weeks_int = [label_to_week[l] for l in sel_week_labels if l in label_to_week]

    return {
        "teams":         sel_team,
        "concepts":      sel_concept,
        "coverages":     sel_coverage,
        "formation":     sel_formation,
        "downs":         sel_downs,
        "seasons":       sel_seasons,
        "weeks":         sel_weeks_int,
        "defteam":       sel_defteam,
        "def_formation": sel_def_formation,
    }


# ── Tab 1 — Find a Play ───────────────────────────────────────────────────────
def render_explorer(filtered_df: pd.DataFrame, full_df: pd.DataFrame):
    if filtered_df.empty:
        st.warning("No plays match the current filters.")
        return

    list_col, detail_col = st.columns([1, 3])

    with list_col:
        sort_choice = st.selectbox(
            "↕ Sort", [f"↕ {k}" for k in SORT_OPTIONS],
            label_visibility="collapsed", key="sel_sort")
        sort_key = sort_choice.replace("↕ ", "")
        sort_col, sort_asc = SORT_OPTIONS[sort_key]
        results = filtered_df.sort_values(sort_col, ascending=sort_asc,
                                          na_position="last").head(20)

        sel_idx = st.session_state.get("selected_play_idx", 0)
        if sel_idx >= len(results):
            sel_idx = 0
            st.session_state["selected_play_idx"] = 0

        for i, (_, row) in enumerate(results.iterrows()):
            label = play_label(i, row)
            if st.button(label, key=f"play_{i}", use_container_width=True):
                st.session_state["selected_play_idx"] = i
                st.rerun()

    with detail_col:
        if results.empty:
            return

        selected_play = results.iloc[sel_idx]
        col_card, col_diagram = st.columns([1, 1])

        with col_card:
            concept_val  = selected_play.get("concept", "—")
            formation_val = selected_play.get("formation_label", "—")
            coverage_val = selected_play.get("coverage", "—")
            yards_val    = selected_play.get("yards_gained")
            epa_val      = selected_play.get("epa")
            down_val     = selected_play.get("down")
            ydstogo_val  = selected_play.get("ydstogo")

            yards_str = f"{int(yards_val)}" if pd.notna(yards_val) else "—"
            epa_str   = f"{epa_val:+.2f}" if pd.notna(epa_val) else "—"

            try:
                down_int = int(down_val)
                ydt_int  = int(ydstogo_val)
                down_str = f"{down_int}{DOWN_SUFFIX.get(down_int,'th')} & {ydt_int}"
            except (TypeError, ValueError):
                down_str = "—"

            concept_color  = CONCEPT_COLORS.get(concept_val, "#6B7280")
            coverage_color = COVERAGE_COLORS.get(coverage_val, "#6B7280")
            formation_color = FORMATION_COLORS.get(formation_val, "#6B7280")

            # Play card
            st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border-radius:12px; padding:16px 20px; margin-bottom:12px;
            border:0.5px solid var(--color-border-tertiary)">
  <p style="font-size:11px; color:var(--color-text-secondary);
            text-transform:uppercase; margin:0 0 8px">{down_str}</p>
  <div style="margin-bottom:12px">
    <p style="font-size:11px; color:var(--color-text-secondary);
              text-transform:uppercase; letter-spacing:0.06em; margin:0 0 4px">Concept</p>
    <span style="padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500;
                 background:{concept_color}22; color:{concept_color};
                 border:1px solid {concept_color}55">{concept_val}</span>
  </div>
  <div style="margin-bottom:12px">
    <p style="font-size:11px; color:var(--color-text-secondary);
              text-transform:uppercase; letter-spacing:0.06em; margin:0 0 4px">Formation</p>
    <span style="padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500;
                 background:{formation_color}22; color:{formation_color};
                 border:1px solid {formation_color}55">{formation_val}</span>
  </div>
  <div>
    <p style="font-size:11px; color:var(--color-text-secondary);
              text-transform:uppercase; letter-spacing:0.06em; margin:0 0 4px">Coverage</p>
    <span style="padding:4px 12px; border-radius:20px; font-size:13px; font-weight:500;
                 background:{coverage_color}22; color:{coverage_color};
                 border:1px solid {coverage_color}55">{coverage_val}</span>
  </div>
</div>
""", unsafe_allow_html=True)

            # Métricas
            m1, m2, m3 = st.columns(3)
            m1.metric("Yards", yards_str)
            m2.metric("EPA", epa_str)
            try:
                first_down = int(yards_val) >= int(ydstogo_val)
                m3.metric("1st Down", "✅" if first_down else "❌")
            except (TypeError, ValueError):
                m3.metric("1st Down", "—")

            # Similar plays
            similar = find_similar_plays(selected_play, filtered_df)
            if not similar.empty:
                st.markdown("**Similar plays**")
                sim_cols = st.columns(len(similar))
                for col, (_, row) in zip(sim_cols, similar.iterrows()):
                    _epa = row.get("epa")
                    _yds = row.get("yards_gained")
                    _dn  = int(row.get("down", 1))
                    _suf = DOWN_SUFFIX.get(_dn, "th")
                    _ydt = int(row.get("ydstogo", 0))
                    _color = "#10B981" if pd.notna(_epa) and _epa > 0 else "#EF4444"
                    with col:
                        st.markdown(
                            f"<div style='background:var(--color-background-secondary);"
                            f"border-radius:10px;border:0.5px solid var(--color-border-tertiary);"
                            f"padding:10px 12px'>"
                            f"<div style='font-size:12px;font-weight:500'>{row.get('concept','—')}</div>"
                            f"<div style='font-size:11px;color:var(--color-text-secondary)'>"
                            f"{_dn}{_suf} & {_ydt} · {row.get('coverage','—')}</div>"
                            f"<div style='font-size:13px;font-weight:500;color:{_color}'>"
                            f"{int(_yds) if pd.notna(_yds) else '—'} yds · {_epa:+.2f} EPA</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        if st.button("View", key=f"sim_{row.name}", use_container_width=True):
                            target = results.index.get_loc(row.name) if row.name in results.index else 0
                            st.session_state["selected_play_idx"] = target
                            st.rerun()

        with col_diagram:
            st.caption(f"📐 {concept_val} · {formation_val}")
            fig = draw_play(selected_play)
            st.plotly_chart(fig, use_container_width=True)


# ── Tab 2 — Analytics ─────────────────────────────────────────────────────────
def render_analytics(filtered_df: pd.DataFrame):
    total        = len(filtered_df)
    avg_epa      = filtered_df["epa"].mean()       if total else 0.0
    success_rate = (filtered_df["epa"] > 0).mean() if total else 0.0
    top_concept  = filtered_df["concept"].mode()[0] if total else "—"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Plays", f"{total:,}")
    k2.metric("Avg EPA",      f"{avg_epa:+.3f}")
    k3.metric("Success Rate", f"{success_rate:.1%}")
    k4.metric("Top Concept",  top_concept)

    st.divider()

    # Concept performance + trend
    st.subheader("Concept performance")
    win_col, _ = st.columns([1, 4])
    with win_col:
        trend_window = st.selectbox(
            "Trend window", [4, 8, "Full season"], index=1,
            key="trend_window",
            format_func=lambda x: f"Trend: last {x} wks" if x != "Full season" else "Trend: full season",
            label_visibility="collapsed")
    w = int(filtered_df["week"].max()) if trend_window == "Full season" else int(trend_window)

    perf = concept_performance(filtered_df)
    if not perf.empty:
        perf_reset = perf.reset_index() if "concept" not in perf.columns else perf.copy()
        perf_trend = add_trend_column(perf_reset, filtered_df, w)
        bar_df     = perf_trend.copy()
        if "concept" not in bar_df.columns:
            bar_df = bar_df.reset_index()
        bar_df = bar_df.sort_values("avg_epa", ascending=True).tail(10)

        fig_bar = px.bar(
            bar_df, x="avg_epa", y="concept", orientation="h",
            color="avg_epa", color_continuous_scale="RdYlGn",
            height=280, template="plotly_white")
        fig_bar.update_layout(
            margin=dict(t=8,b=8,l=8,r=8), coloraxis_showscale=False,
            xaxis_title="", yaxis_title="",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

        display_cols = [c for c in perf_trend.columns if c not in ("spark","trend_delta")]
        st.dataframe(
            style_table(perf_trend[display_cols], pct_cols=["success_rate"], epa_cols=["avg_epa"]),
            use_container_width=True)

        with st.expander("📈 Weekly sparklines", expanded=False):
            spark_cols = st.columns(3)
            for i, (_, row) in enumerate(perf_trend.iterrows()):
                spark = row.get("spark", [])
                if len(spark) < 2:
                    continue
                with spark_cols[i % 3]:
                    delta_val = row.get("trend_delta", 0)
                    color     = ("#10B981" if delta_val > 0.10
                                 else "#EF4444" if delta_val < -0.10 else "#9CA3AF")
                    fig_sp = go.Figure(go.Scatter(
                        y=spark, mode="lines+markers",
                        line=dict(color=color, width=2),
                        marker=dict(size=5, color=color)))
                    fig_sp.update_layout(
                        height=100, margin=dict(t=4,b=4,l=4,r=4),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                        yaxis=dict(showgrid=False, showticklabels=False, zeroline=True,
                                   zerolinecolor="#E5E7EB", zerolinewidth=1),
                        showlegend=False)
                    concept_name = row.get("concept", row.name if hasattr(row,"name") else "")
                    badge = row.get("trend_badge","")
                    st.caption(f"**{concept_name}** · {badge} · {delta_val:+.2f}")
                    st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Not enough data for the current filters.")

    # Concept vs Coverage + Third Down
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Concept vs Coverage")
        cvs = concept_vs_coverage(filtered_df).head(20)
        if not cvs.empty:
            st.dataframe(
                style_table(cvs, pct_cols=["success_rate"], epa_cols=["avg_epa"]),
                use_container_width=True)
            top_concepts  = filtered_df.groupby("concept")["epa"].count().nlargest(8).index.tolist()
            top_coverages = filtered_df.groupby("coverage")["epa"].count().nlargest(6).index.tolist()
            heat_df = (
                filtered_df[
                    filtered_df["concept"].isin(top_concepts) &
                    filtered_df["coverage"].isin(top_coverages)
                ]
                .groupby(["concept","coverage"])["epa"].mean()
                .unstack(fill_value=0)
                .reindex(index=top_concepts, columns=top_coverages, fill_value=0)
            )
            fig_heat = go.Figure(go.Heatmap(
                z=heat_df.values, x=heat_df.columns.tolist(), y=heat_df.index.tolist(),
                colorscale="RdYlGn",
                hovertemplate="%{y} vs %{x}<br>Avg EPA: %{z:.3f}<extra></extra>",
                colorbar=dict(title="Avg EPA", thickness=12, len=0.8)))
            fig_heat.update_layout(
                height=320, margin=dict(t=8,b=8,l=8,r=8),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Not enough data.")

    with col_right:
        st.subheader("Third Down Analysis")
        tda = third_down_analysis(filtered_df)
        if not tda.empty:
            st.dataframe(
                style_table(tda, pct_cols=["success_rate","conversion_rate"], epa_cols=["avg_epa"]),
                use_container_width=True)
        else:
            st.info("Not enough data.")

    # Formation vs Def Formation
    st.divider()
    st.subheader("Formation vs Defensive Formation")
    fvf = formation_vs_formation(filtered_df).head(30)
    if not fvf.empty:
        st.dataframe(
            style_table(fvf, pct_cols=["success_rate"], epa_cols=["avg_epa"]),
            use_container_width=True)
    else:
        st.info("Not enough data.")