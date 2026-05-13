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
from components.ai_scout import render_ai_scout

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
                default=[], key="sel_team",
                format_func=lambda x: TEAM_NAMES.get(x, x))
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
def render_explorer(filtered_df, full_df):
    if filtered_df.empty:
        st.warning("No plays match the current filters.")
        return

    sort_col_ui, _ = st.columns([2, 8])
    with sort_col_ui:
        sort_choice = st.selectbox(
            "Sort", list(SORT_OPTIONS.keys()),
            label_visibility="collapsed", key="sel_sort"
        )
    sort_col, sort_asc = SORT_OPTIONS[sort_choice]
    results = filtered_df.sort_values(
        sort_col, ascending=sort_asc, na_position="last"
    ).head(20).reset_index(drop=True)

    if "selected_play_idx" not in st.session_state:
        st.session_state["selected_play_idx"] = 0
    sel_idx = min(st.session_state["selected_play_idx"], len(results) - 1)
    selected = results.iloc[sel_idx]

    col_list, col_detail, col_right = st.columns([2, 3, 3])

    st.markdown("""
<style>
div[data-testid="stVerticalBlock"] div.stButton > button {
    background: transparent;
    border: none;
    border-bottom: 0.5px solid var(--color-border-tertiary);
    border-radius: 0;
    padding: 10px 4px;
    text-align: left;
    width: 100%;
}
div[data-testid="stVerticalBlock"] div.stButton > button:hover {
    background: var(--color-background-secondary);
    border-color: var(--color-border-tertiary);
}
</style>
""", unsafe_allow_html=True)
    
    st.markdown("""
<style>
div[data-testid="stVerticalBlock"] div.stButton > button {
    height: 28px !important;
    min-height: 28px !important;
    padding: 0 8px !important;
    border: 0.5px solid var(--color-border-tertiary) !important;
    background: transparent !important;
    box-shadow: none !important;
    font-size: 11px !important;
    color: var(--color-text-tertiary) !important;
    border-radius: 6px !important;
    width: auto !important;
    white-space: nowrap !important;
}
div[data-testid="stVerticalBlock"] div.stButton > button:hover {
    background: var(--color-background-secondary) !important;
    border-color: var(--color-border-secondary) !important;
}
div[data-testid="stVerticalBlock"] div.stButton {
    margin: 0 !important;
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

    with col_list:
        st.caption(f"{len(results)} plays")
        with st.container(height=720):
            for i, row in results.iterrows():
                try:
                    dn = int(row["down"]); ydt = int(row["ydstogo"])
                    down_str_item = f"{dn}{DOWN_SUFFIX.get(dn,'th')}&{ydt}"
                except:
                    down_str_item = "—"
                yards    = row.get("yards_gained")
                epa      = row.get("epa")
                team     = row.get("posteam", "?")
                concept  = row.get("concept", "?")
                yards_str = f"{int(yards)} yds" if pd.notna(yards) else "—"
                epa_str   = f"{epa:+.2f}" if pd.notna(epa) else "—"
                epa_color = "#3B6D11" if pd.notna(epa) and epa >= 0 else "#A32D2D"
                is_active = sel_idx == i
                active_style = "border-left:2px solid #378ADD;" if is_active else "border-left:2px solid transparent;"

                col_text, col_btn = st.columns([1.5, 1])
                with col_text:
                    st.markdown(f"""
        <div style="padding:8px 4px;{active_style}">
        <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:3px;">
            <span style="font-size:11px;color:var(--color-text-tertiary);min-width:18px;">{i+1}.</span>
            <span style="font-size:13px;font-weight:500;color:var(--color-text-primary);">{team}</span>
            <span style="font-size:13px;color:#378ADD;">{concept}</span>
        </div>
        <div style="display:flex;gap:6px;padding-left:24px;">
            <span style="font-size:12px;color:var(--color-text-secondary);">{down_str_item}</span>
            <span style="font-size:12px;color:var(--color-text-tertiary);">·</span>
            <span style="font-size:12px;color:var(--color-text-secondary);">{yards_str}</span>
            <span style="font-size:12px;color:var(--color-text-tertiary);">·</span>
            <span style="font-size:12px;font-weight:500;color:{epa_color};">{epa_str}</span>
        </div>
        </div>
        """, unsafe_allow_html=True)
                with col_btn:
                    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                    if st.button("Select this play", key=f"play_{i}"):
                        st.session_state["selected_play_idx"] = i
                        st.rerun()

    with col_detail:
        concept_val    = selected.get("concept", "—")
        formation_val  = selected.get("formation_label", "—")
        coverage_val   = selected.get("coverage", "—")
        yards_val      = selected.get("yards_gained")
        epa_val        = selected.get("epa")
        down_val       = selected.get("down")
        ydstogo_val    = selected.get("ydstogo")

        try:
            dn = int(down_val); ydt = int(ydstogo_val)
            down_str = f"{dn}{DOWN_SUFFIX.get(dn,'th')} & {ydt}"
        except:
            down_str = "—"

        concept_color   = CONCEPT_COLORS.get(concept_val, "#6B7280")
        coverage_color  = COVERAGE_COLORS.get(coverage_val, "#6B7280")
        formation_color = FORMATION_COLORS.get(formation_val, "#6B7280")

        # ── Badges ───────────────────────────────────────
        st.markdown(f"""
<div style="margin-bottom:14px;">
  <div style="font-size:32px;font-weight:500;color:var(--color-text-primary);
              margin-bottom:14px;">{down_str}</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
    <div style="background:{concept_color}22;border:1px solid {concept_color}55;
                border-radius:10px;padding:10px 12px;">
      <p style="font-size:10px;color:{concept_color};text-transform:uppercase;
                letter-spacing:.06em;margin:0 0 4px;opacity:0.8">Concept</p>
      <p style="font-size:14px;font-weight:500;color:{concept_color};margin:0;">
        {concept_val}</p>
    </div>
    <div style="background:{formation_color}22;border:1px solid {formation_color}55;
                border-radius:10px;padding:10px 12px;">
      <p style="font-size:10px;color:{formation_color};text-transform:uppercase;
                letter-spacing:.06em;margin:0 0 4px;opacity:0.8">Formation</p>
      <p style="font-size:14px;font-weight:500;color:{formation_color};margin:0;">
        {formation_val}</p>
    </div>
    <div style="background:{coverage_color}22;border:1px solid {coverage_color}55;
                border-radius:10px;padding:10px 12px;">
      <p style="font-size:10px;color:{coverage_color};text-transform:uppercase;
                letter-spacing:.06em;margin:0 0 4px;opacity:0.8">Coverage</p>
      <p style="font-size:14px;font-weight:500;color:{coverage_color};margin:0;">
        {coverage_val}</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        # ── Métricas grandes ─────────────────────────────
        st.markdown("<p style='font-size:13px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>RESULT</p>", unsafe_allow_html=True)
        yards_str = f"{int(yards_val)}" if pd.notna(yards_val) else "—"
        epa_str   = f"{epa_val:+.2f}" if pd.notna(epa_val) else "—"
        try:
            first_down = int(yards_val) >= int(ydstogo_val)
            fd_str = "✓ Yes" if first_down else "✗ No"
            fd_color = "color:#3B6D11" if first_down else "color:#A32D2D"
        except:
            fd_str = "—"; fd_color = ""

        epa_color = "color:#3B6D11" if pd.notna(epa_val) and epa_val >= 0 else "color:#A32D2D"

        st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:4px;">
  <div style="background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);
              border-radius:8px;padding:14px 12px;text-align:center;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:6px;">Yards</div>
    <div style="font-size:28px;font-weight:500;">{yards_str}</div>
  </div>
  <div style="background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);
              border-radius:8px;padding:14px 12px;text-align:center;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:6px;">EPA</div>
    <div style="font-size:28px;font-weight:500;{epa_color}">{epa_str}</div>
  </div>
  <div style="background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);
              border-radius:8px;padding:14px 12px;text-align:center;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:6px;">1st Down</div>
    <div style="font-size:20px;font-weight:500;{fd_color}">{fd_str}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        # ── Concept vs Coverage bars ──────────────────────
        st.markdown("<p style='font-size:13px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>CONCEPT VS COVERAGE</p>", unsafe_allow_html=True)
        cvs = concept_vs_coverage(filtered_df)
        if not cvs.empty and concept_val in cvs["concept"].values:
            concept_cvs = (
                cvs[cvs["concept"] == concept_val]
                .sort_values("avg_epa", ascending=False)
                .head(5)
            )
            max_epa = concept_cvs["avg_epa"].abs().max() or 1
            bars_html = ""
            for _, row in concept_cvs.iterrows():
                pct   = min(abs(row["avg_epa"]) / max_epa * 100, 100)
                color = "#3B6D11" if row["avg_epa"] >= 0 else "#A32D2D"
                cov   = row["coverage"]
                active = "border:1px solid #378ADD;" if row["coverage"] == coverage_val else ""
                bars_html += f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
  <span style="font-size:15px;color:var(--color-text-secondary);
               width:130px;flex-shrink:0;{active}">{cov}</span>
  <div style="flex:1;height:6px;background:var(--color-border-tertiary);
              border-radius:3px;overflow:hidden;">
    <div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:3px;"></div>
  </div>
  <span style="font-size:15px;color:var(--color-text-secondary);
               width:42px;text-align:right;">{row['avg_epa']:+.2f}</span>
</div>"""
            st.markdown(f"""
<div style="background:var(--color-background-primary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:8px;padding:12px 14px;">
  {bars_html}
</div>
""", unsafe_allow_html=True)
        else:
            st.caption("Not enough data")

        st.divider()

        # ── Context ───────────────────────────────────────
        st.markdown("<p style='font-size:13px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>CONTEXT</p>", unsafe_allow_html=True)
        perf = concept_performance(filtered_df)
        if not perf.empty and concept_val in perf.index:
            c_avg_epa     = perf.loc[concept_val, "avg_epa"]
            c_success     = perf.loc[concept_val, "success_rate"]
            c_plays       = int(perf.loc[concept_val, "plays"])
            deviation     = (epa_val - c_avg_epa) if pd.notna(epa_val) else None
            dev_str       = f"{deviation:+.2f} above avg" if deviation and deviation >= 0 else f"{deviation:.2f} below avg" if deviation else "—"
            dev_color     = "#3B6D11" if deviation and deviation >= 0 else "#A32D2D"
            avg_color     = "#3B6D11" if c_avg_epa >= 0 else "#A32D2D"

            st.markdown(f"""
<div style="background:var(--color-background-primary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:8px;padding:12px 14px;">
  <div style="display:flex;justify-content:space-between;
              padding:6px 0;border-bottom:0.5px solid var(--color-border-tertiary);">
    <span style="font-size:15px;color:gray;">Concept avg EPA</span>
    <span style="font-size:18px;font-weight:500;color:{avg_color};">{c_avg_epa:+.3f}</span>
  </div>
  <div style="display:flex;justify-content:space-between;
              padding:6px 0;border-bottom:0.5px solid var(--color-border-tertiary);">
    <span style="font-size:15px;color:gray;">This play vs avg</span>
    <span style="font-size:18px;font-weight:500;color:{dev_color};">{dev_str}</span>
  </div>
  <div style="display:flex;justify-content:space-between;
              padding:6px 0;border-bottom:0.5px solid var(--color-border-tertiary);">
    <span style="font-size:15px;color:gray;">Success rate</span>
    <span style="font-size:18px;font-weight:500;">{c_success:.1%}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:6px 0;">
    <span style="font-size:15px;color:gray;">Plays in dataset</span>
    <span style="font-size:18px;font-weight:500;">{c_plays:,}</span>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.caption("Not enough data")

    with col_right:
        st.caption(f"📐 {concept_val} · {formation_val}")
        fig = draw_play(selected)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
        st.divider()
        render_ai_scout(
            {"concept": concept_val, "coverage": coverage_val,
             "formation": formation_val, "down": down_val},
            filtered_df
        )

    similar = find_similar_plays(selected, filtered_df)
    if not similar.empty:
        st.divider()
        st.markdown("<p style='font-size:13px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>Similar plays</p>", unsafe_allow_html=True)
        sim_cols = st.columns(len(similar))
        for col, (_, row) in zip(sim_cols, similar.iterrows()):
            _epa   = row.get("epa")
            _yds   = row.get("yards_gained")
            _dn    = int(row.get("down", 1))
            _suf   = DOWN_SUFFIX.get(_dn, "th")
            _ydt   = int(row.get("ydstogo", 0))
            _color = "#10B981" if pd.notna(_epa) and _epa > 0 else "#EF4444"
            with col:
                st.markdown(
                    f"<div style='background:var(--color-background-secondary);"
                    f"border-radius:10px;border:0.5px solid var(--color-border-tertiary);"
                    f"padding:14px 16px'>"
                    f"<div style='font-size:15px;font-weight:500;margin-bottom:4px'>{row.get('concept','—')}</div>"
                    f"<div style='font-size:13px;color:gray;margin-bottom:6px'>"
                    f"{row.get('posteam','?')} · {_dn}{_suf}&{_ydt} · {row.get('coverage','—')}</div>"
                    f"<div style='font-size:16px;font-weight:500;color:{_color}'>"
                    f"{int(_yds) if pd.notna(_yds) else '—'} yds · "
                    f"{_epa:+.2f} EPA</div></div>",
                    unsafe_allow_html=True
                )
                if st.button("View", key=f"sim_{row.name}",
                             use_container_width=True):
                    match = results[results.index == row.name]
                    if not match.empty:
                        st.session_state["selected_play_idx"] = match.index[0]
                    st.rerun()

def render_analytics(filtered_df: pd.DataFrame, full_df: pd.DataFrame = None):
    total        = len(filtered_df)
    avg_epa      = filtered_df["epa"].mean()        if total else 0.0
    success_rate = (filtered_df["epa"] > 0).mean()  if total else 0.0
    top_concept  = filtered_df["concept"].mode()[0]  if total else "—"

    # Benchmarks desde dataset completo
    if full_df is not None and not full_df.empty:
        base_epa     = full_df["epa"].mean()
        base_success = (full_df["epa"] > 0).mean()
    else:
        base_epa     = 0.0
        base_success = 0.47

    # Concepto más eficiente (distinto al más usado)
    perf_all = concept_performance(filtered_df)
    top_efficient = perf_all.index[0] if not perf_all.empty else "—"

    # Indicadores
    sample_ind = "✓ Muestra suficiente" if total > 500 else "→ Muestra moderada" if total > 100 else "⚠️ Muestra insuficiente"
    sample_color = "#3B6D11" if total > 500 else "#92610A" if total > 100 else "#A32D2D"
    sample_bg    = "#EAF3DE" if total > 500 else "#FEF3CD" if total > 100 else "#FDE8E8"
    sample_border = "#97C459" if total > 500 else "#F5CC6A" if total > 100 else "#F5A0A0"

    epa_diff  = avg_epa - base_epa
    epa_ind   = "↑ Sobre el promedio" if epa_diff > 0.05 else "↓ Bajo el promedio" if epa_diff < -0.05 else "→ Equilibrado"
    epa_color = "#3B6D11" if epa_diff > 0.05 else "#A32D2D" if epa_diff < -0.05 else "#92610A"
    epa_bg    = "#EAF3DE" if epa_diff > 0.05 else "#FDE8E8" if epa_diff < -0.05 else "#FEF3CD"
    epa_border = "#97C459" if epa_diff > 0.05 else "#F5A0A0" if epa_diff < -0.05 else "#F5CC6A"

    sr_diff   = success_rate - base_success
    sr_ind    = "↑ Sobre el promedio" if sr_diff > 0.02 else "↓ Bajo el promedio" if sr_diff < -0.02 else "→ En el promedio"
    sr_color  = "#3B6D11" if sr_diff > 0.02 else "#A32D2D" if sr_diff < -0.02 else "#92610A"
    sr_bg     = "#EAF3DE" if sr_diff > 0.02 else "#FDE8E8" if sr_diff < -0.02 else "#FEF3CD"
    sr_border = "#97C459" if sr_diff > 0.02 else "#F5A0A0" if sr_diff < -0.02 else "#F5CC6A"

    concept_insight = f"<em>{top_concept}</em> es el más usado." if top_concept == top_efficient else f"<em>{top_concept}</em> es el más usado pero <em>{top_efficient}</em> lidera en EPA."

    st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">
  <div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
              border-radius:10px;padding:20px 22px;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Total plays</div>
    <div style="font-size:34px;font-weight:500;margin-bottom:6px;">{total:,}</div>
    <div style="font-size:13px;color:var(--color-text-secondary);margin-bottom:8px;">Jugadas analizadas con los filtros actuales.</div>
    <span style="font-size:11px;padding:2px 8px;border-radius:20px;background:{sample_bg};
                 color:{sample_color};border:1px solid {sample_border};">{sample_ind}</span>
  </div>
  <div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
              border-radius:10px;padding:20px 22px;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Avg EPA</div>
    <div style="font-size:34px;font-weight:500;color:{epa_color};margin-bottom:6px;">{avg_epa:+.3f}</div>
    <div style="font-size:13px;color:var(--color-text-secondary);margin-bottom:8px;">
      {f"{'Mejor' if epa_diff >= 0 else 'Peor'} que el promedio general por {abs(epa_diff):.3f} pts."}</div>
    <span style="font-size:11px;padding:2px 8px;border-radius:20px;background:{epa_bg};
                 color:{epa_color};border:1px solid {epa_border};">{epa_ind}</span>
  </div>
  <div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
              border-radius:10px;padding:20px 22px;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Success Rate</div>
    <div style="font-size:34px;font-weight:500;color:{sr_color};margin-bottom:6px;">{success_rate:.1%}</div>
    <div style="font-size:13px;color:var(--color-text-secondary);margin-bottom:8px;">
      {f"{'Mayor' if sr_diff >= 0 else 'Menor'} efectividad que el promedio general ({base_success:.1%})."}</div>
    <span style="font-size:11px;padding:2px 8px;border-radius:20px;background:{sr_bg};
                 color:{sr_color};border:1px solid {sr_border};">{sr_ind}</span>
  </div>
  <div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
              border-radius:10px;padding:20px 22px;">
    <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Top Concept</div>
    <div style="font-size:28px;font-weight:500;margin-bottom:6px;">{top_concept}</div>
    <div style="font-size:13px;color:var(--color-text-secondary);margin-bottom:8px;">{concept_insight}</div>
    <span style="font-size:11px;padding:2px 8px;border-radius:20px;background:#E6F1FB;
                 color:#185FA5;border:1px solid #85B7EB;">↗ {top_efficient} es más eficiente</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    render_counter_intelligence(filtered_df)

    st.divider()

    # ── Concept Performance ─────────────────────────────
    st.markdown("### 📈 Concept Performance")
    st.caption("¿Qué conceptos están subiendo y cuáles perdiendo efectividad?")

    perf = concept_performance(filtered_df)
    if perf.empty:
        st.info("Not enough data for the current filters.")
    else:
        win_col, _ = st.columns([2, 6])
        with win_col:
            trend_window = st.selectbox(
                "Trend window", [4, 8, "Full season"], index=1,
                key="trend_window",
                format_func=lambda x: f"Últimas {x} semanas" if x != "Full season" else "Temporada completa",
                label_visibility="collapsed"
            )
        w = int(filtered_df["week"].max()) if trend_window == "Full season" else int(trend_window)
        perf_reset = perf.reset_index() if "concept" not in perf.columns else perf.copy()
        perf_trend = add_trend_column(perf_reset, filtered_df, w)

        card_cols = st.columns(3)
        for i, (_, row) in enumerate(perf_trend.iterrows()):
            concept_name = row.get("concept", row.name if hasattr(row, "name") else "")
            epa_val      = row.get("avg_epa", 0)
            yards_val    = row.get("avg_yards", 0)
            success_val  = row.get("success_rate", 0)
            plays_val    = int(row.get("plays", 0))
            delta_val    = row.get("trend_delta", 0)
            badge        = row.get("trend_badge", "→ Stable")
            spark        = row.get("spark", [])

            trend        = "hot" if delta_val > 0.10 else "cool" if delta_val < -0.10 else "stable"
            border_color = "#F59E0B" if trend == "hot" else "#60A5FA" if trend == "cool" else "var(--color-border-tertiary)"
            badge_style  = "background:#FEF3CD;color:#92610A;border:1px solid #F5CC6A;" if trend == "hot" else                            "background:#EFF6FF;color:#1D4ED8;border:1px solid #93C5FD;" if trend == "cool" else                            "background:var(--color-background-primary);color:var(--color-text-tertiary);border:0.5px solid var(--color-border-tertiary);"
            epa_color    = "#3B6D11" if epa_val >= 0 else "#A32D2D"
            insight      = f"Ganando +{delta_val:.2f} EPA vs semanas anteriores" if trend == "hot" else                            f"Perdiendo {abs(delta_val):.2f} EPA vs semanas anteriores" if trend == "cool" else                            "Sin cambio significativo en tendencia reciente"

            spark_svg = ""
            if len(spark) >= 2:
                svg_w, svg_h = 200, 40
                mn, mx = min(spark), max(spark)
                rng = mx - mn or 1
                pts = " ".join([
                    f"{int((j/(len(spark)-1))*svg_w)},{int(svg_h - ((v-mn)/rng)*(svg_h-6) - 3)}"
                    for j, v in enumerate(spark)
                ])
                spark_color = "#F59E0B" if trend == "hot" else "#60A5FA" if trend == "cool" else "#9CA3AF"
                spark_svg = f'''
<svg viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;height:40px;display:block;margin-top:8px;">
  <polyline points="{pts}" fill="none" stroke="{spark_color}" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''

            with card_cols[i % 3]:
                st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-left:3px solid {border_color};
            border-radius:10px;padding:14px 16px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
    <span style="font-size:14px;font-weight:500;color:var(--color-text-primary);">{concept_name}</span>
    <span style="font-size:11px;padding:2px 8px;border-radius:20px;{badge_style}">{badge}</span>
  </div>
  <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:6px;">
    <span style="font-size:22px;font-weight:500;color:{epa_color};">{epa_val:+.3f}</span>
    <span style="font-size:11px;color:var(--color-text-tertiary);">avg EPA</span>
  </div>
  <div style="display:flex;gap:14px;margin-bottom:4px;">
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Plays</div>
      <div style="font-size:12px;font-weight:500;">{plays_val:,}</div>
    </div>
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Yards</div>
      <div style="font-size:12px;font-weight:500;">{yards_val:.1f}</div>
    </div>
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Success</div>
      <div style="font-size:12px;font-weight:500;">{success_val:.1%}</div>
    </div>
  </div>
  {spark_svg}
  <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:6px;font-style:italic;">{insight}</div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Concept vs Coverage ───────────────────────────────────────────────────
    st.markdown("### 🎯 Concept vs Coverage")
    st.caption("¿Qué combinación es más y menos efectiva?")

    cvs = concept_vs_coverage(filtered_df)
    if not cvs.empty:
        best_row  = cvs.loc[cvs["avg_epa"].idxmax()]
        worst_row = cvs.loc[cvs["avg_epa"].idxmin()]
        cov_avg   = cvs.groupby("coverage")["avg_epa"].mean()
        top_cov      = cov_avg.idxmax()
        top_cov_epa  = cov_avg.max()

        best_epa_color    = "#3B6D11" if best_row["avg_epa"] >= 0 else "#A32D2D"
        worst_epa_color   = "#3B6D11" if worst_row["avg_epa"] >= 0 else "#A32D2D"
        top_cov_epa_color = "#3B6D11" if top_cov_epa >= 0 else "#A32D2D"

        st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;padding:14px 18px;margin-bottom:16px;">
  <p style="font-size:10px;color:gray;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:6px;">Insight</p>
  <p style="font-size:16px;color:var(--color-text-primary);line-height:1.6;margin:0;">
    El matchup más efectivo es
    <span style="color:#378ADD;font-weight:500;">{best_row['concept']}</span>
    vs <span style="color:#378ADD;font-weight:500;">{best_row['coverage']}</span>
    con un EPA promedio de
    <span style="color:{best_epa_color};font-weight:500;">{best_row['avg_epa']:+.3f}</span>.<br><br>
    El menos efectivo es
    <span style="color:#378ADD;font-weight:500;">{worst_row['concept']}</span>
    vs <span style="color:#378ADD;font-weight:500;">{worst_row['coverage']}</span>
    (<span style="color:{worst_epa_color};font-weight:500;">{worst_row['avg_epa']:+.3f}</span>).
    La cobertura que concede más EPA en promedio es
    <span style="color:#378ADD;font-weight:500;">{top_cov}</span>
    (<span style="color:{top_cov_epa_color};font-weight:500;">{top_cov_epa:+.3f}</span>).
  </p>
</div>
""", unsafe_allow_html=True)

        cvc_left, cvc_right = st.columns(2)

        with cvc_left:
            raw_pivot = (
                filtered_df.groupby(["concept", "coverage"])["epa"].mean()
                .unstack()
            )
            concept_order = (
                filtered_df.groupby("concept")["epa"].mean()
                .sort_values(ascending=False)
                .index.tolist()
            )
            concept_order = [c for c in concept_order if c in raw_pivot.index]
            coverage_order = raw_pivot.columns.tolist()
            heat_df = raw_pivot.reindex(index=concept_order, columns=coverage_order)
            cell_text = [
                ["—" if pd.isna(v) else f"{v:+.2f}" for v in row]
                for row in heat_df.values
            ]
            fig_heat = go.Figure(go.Heatmap(
                z=heat_df.values,
                x=heat_df.columns.tolist(),
                y=heat_df.index.tolist(),
                text=cell_text,
                texttemplate="%{text}",
                textfont={"size": 10, "color": "white"},
                colorscale="RdYlGn",
                hovertemplate="%{y} vs %{x}<br>Avg EPA: %{z:.3f}<extra></extra>",
                colorbar=dict(title="Avg EPA", thickness=12, len=0.8)))
            fig_heat.update_layout(
                height=400, margin=dict(t=8, b=8, l=8, r=8),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

        with cvc_right:
            top4    = cvs.nlargest(4, "avg_epa").reset_index(drop=True)
            bottom3 = cvs.nsmallest(3, "avg_epa").reset_index(drop=True)

            st.markdown("""<p style="font-size:12px;color:gray;text-transform:uppercase;
letter-spacing:.06em;margin-bottom:6px;">Top 4 mejores matchups</p>""",
                        unsafe_allow_html=True)

            for _, row in top4.iterrows():
                ec = "#3B6D11" if row["avg_epa"] >= 0 else "#A32D2D"
                st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:9px 12px;border-bottom:0.5px solid var(--color-border-tertiary);">
  <div>
    <span style="font-size:15px;font-weight:500;color:var(--color-text-primary);">{row['concept']}</span>
    <span style="font-size:13px;color:var(--color-text-tertiary);margin:0 4px;">vs</span>
    <span style="font-size:13px;color:#378ADD;">{row['coverage']}</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:13px;color:var(--color-text-tertiary);">{int(row['plays'])} plays</span>
    <span style="font-size:18px;font-weight:500;color:{ec};">{row['avg_epa']:+.3f}</span>
    <span style="font-size:10px;padding:1px 6px;border-radius:20px;
                background:#EAF3DE;color:#3B6D11;border:1px solid #97C459;">Best</span>
  </div>
</div>
""", unsafe_allow_html=True)

            st.markdown("""<div style="height:1px;background:var(--color-border-tertiary);margin:10px 0;"></div>
<p style="font-size:12px;color:gray;text-transform:uppercase;
letter-spacing:.06em;margin-bottom:6px;">3 peores matchups</p>""",
                        unsafe_allow_html=True)

            for _, row in bottom3.iterrows():
                ec = "#3B6D11" if row["avg_epa"] >= 0 else "#A32D2D"
                st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:9px 12px;border-bottom:0.5px solid var(--color-border-tertiary);">
  <div>
    <span style="font-size:15px;font-weight:500;color:var(--color-text-primary);">{row['concept']}</span>
    <span style="font-size:13px;color:var(--color-text-tertiary);margin:0 4px;">vs</span>
    <span style="font-size:13px;color:#378ADD;">{row['coverage']}</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:13px;color:var(--color-text-tertiary);">{int(row['plays'])} plays</span>
    <span style="font-size:18px;font-weight:500;color:{ec};">{row['avg_epa']:+.3f}</span>
    <span style="font-size:10px;padding:1px 6px;border-radius:20px;
                background:#FDE8E8;color:#A32D2D;border:1px solid #F5A0A0;">Avoid</span>
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Not enough data.")

    st.divider()

    # ── Third Down Analysis ───────────────────────────────────────────────────
    st.markdown("### 🏈 Third Down Analysis")
    st.caption("¿Qué conceptos convierten mejor en 3ra oportunidad?")

    tda = third_down_analysis(filtered_df)
    if tda.empty:
        st.info("Not enough data.")
    else:
        tda_sorted = tda.sort_values("conversion_rate", ascending=False)
        best  = tda_sorted.iloc[0]
        worst = tda_sorted.iloc[-1]

        best_concept  = best.name
        worst_concept = worst.name
        best_cr   = best["conversion_rate"]
        worst_cr  = worst["conversion_rate"]
        best_epa  = best["avg_epa"]
        best_epa_color  = "#3B6D11" if best_epa >= 0 else "#A32D2D"
        worst_cr_color  = "#3B6D11" if worst_cr >= 0.5 else "#92610A" if worst_cr >= 0.35 else "#A32D2D"

        st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;padding:14px 18px;margin-bottom:16px;">
  <p style="font-size:10px;color:gray;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:6px;">Insight</p>
  <p style="font-size:15px;color:var(--color-text-primary);line-height:1.6;margin:0;">
    El concepto con mayor tasa de conversión en 3ra oportunidad es
    <span style="color:#378ADD;font-weight:500;">{best_concept}</span>
    con un <span style="color:#3B6D11;font-weight:500;">{best_cr:.1%}</span>
    de conversión y un EPA promedio de
    <span style="color:{best_epa_color};font-weight:500;">{best_epa:+.3f}</span>.<br><br>
    El concepto con menor conversión es
    <span style="color:#378ADD;font-weight:500;">{worst_concept}</span>
    (<span style="color:{worst_cr_color};font-weight:500;">{worst_cr:.1%}</span>)
    — considerar alternativas en situaciones de 3ra oportunidad corta.
  </p>
</div>
""", unsafe_allow_html=True)

        card_cols = st.columns(3)
        for i, (concept, row) in enumerate(tda_sorted.iterrows()):
            cr       = row["conversion_rate"]
            avg_epa  = row["avg_epa"]
            avg_yds  = row["avg_yards"]
            plays    = int(row["plays"])
            bar_pct  = int(cr * 100)

            cr_color  = "#3B6D11" if cr >= 0.5 else "#92610A" if cr >= 0.35 else "#A32D2D"
            epa_color = "#3B6D11" if avg_epa >= 0 else "#A32D2D"

            with card_cols[i % 3]:
                st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;padding:14px 16px;margin-bottom:10px;">
  <div style="margin-bottom:10px;">
    <div style="font-size:15px;font-weight:500;color:var(--color-text-primary);margin-bottom:2px;">{concept}</div>
    <div style="font-size:11px;color:gray;">{plays:,} plays</div>
  </div>
  <div style="font-size:28px;font-weight:500;color:{cr_color};margin-bottom:6px;">{cr:.1%}</div>
  <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Conversion rate</div>
  <div style="width:100%;height:5px;background:var(--color-border-tertiary);
              border-radius:3px;overflow:hidden;margin-bottom:12px;">
    <div style="width:{bar_pct}%;height:100%;background:{cr_color};border-radius:3px;"></div>
  </div>
  <div style="display:flex;gap:16px;">
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Avg EPA</div>
      <div style="font-size:13px;font-weight:500;color:{epa_color};">{avg_epa:+.3f}</div>
    </div>
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Avg Yards</div>
      <div style="font-size:13px;font-weight:500;">{avg_yds:.1f}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    
    st.divider()

    # ── Formation vs Defense ──────────────────────────────────────────────────
    st.markdown("### 🏟️ Formation vs Defense")
    st.caption("¿Qué formación funciona mejor contra cada defensa?")

    fvf = formation_vs_formation(filtered_df)
    if fvf.empty:
        st.info("Not enough data.")
    else:
        best_row      = fvf.loc[fvf["avg_epa"].idxmax()]
        best_epa_color = "#3B6D11" if best_row["avg_epa"] >= 0 else "#A32D2D"

        def_plays  = fvf.groupby("def_formation")["plays"].sum()
        top_def    = def_plays.idxmax()
        top_def_rows = fvf[fvf["def_formation"] == top_def].sort_values("avg_epa", ascending=False)
        best_ctr   = top_def_rows.iloc[0] if not top_def_rows.empty else None
        if best_ctr is not None:
            ctr_epa_color = "#3B6D11" if best_ctr["avg_epa"] >= 0 else "#A32D2D"
            counter_line  = (
                f'La defensa más frecuente es <span style="color:#378ADD;font-weight:500;">{top_def}</span>'
                f' — la formación que mejor la contrarresta es'
                f' <span style="color:#378ADD;font-weight:500;">{best_ctr["formation_label"]}</span>'
                f' (<span style="color:{ctr_epa_color};font-weight:500;">{best_ctr["avg_epa"]:+.3f} EPA</span>).'
            )
        else:
            counter_line = ""

        st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;padding:14px 18px;margin-bottom:16px;">
  <p style="font-size:10px;color:gray;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:6px;">Insight</p>
  <p style="font-size:15px;color:var(--color-text-primary);line-height:1.6;margin:0;">
    El mejor matchup ofensivo es
    <span style="color:#378ADD;font-weight:500;">{best_row['formation_label']}</span>
    vs <span style="color:#378ADD;font-weight:500;">{best_row['def_formation']}</span>
    con un EPA promedio de
    <span style="color:{best_epa_color};font-weight:500;">{best_row['avg_epa']:+.3f}</span>.<br><br>
    {counter_line}
  </p>
</div>
""", unsafe_allow_html=True)

        fvf_left, fvf_right = st.columns(2)

        with fvf_left:
            st.markdown(
                '<p style="font-size:11px;color:gray;text-transform:uppercase;'
                'letter-spacing:.08em;margin-bottom:10px;">Por formación defensiva → mejor ataque</p>',
                unsafe_allow_html=True)

            def_order = (
                fvf.groupby("def_formation")["avg_epa"].max()
                .sort_values(ascending=False)
                .index.tolist()
            )
            for def_form in def_order:
                group      = (fvf[fvf["def_formation"] == def_form]
                              .sort_values("avg_epa", ascending=False)
                              .head(3))
                group_list = list(group.iterrows())
                rows_html  = ""
                for j, (_, row) in enumerate(group_list):
                    ec        = "#3B6D11" if row["avg_epa"] >= 0 else "#A32D2D"
                    is_last   = j == len(group_list) - 1
                    border    = "" if is_last else "border-bottom:0.5px solid var(--color-border-tertiary);"
                    pill      = ('<span style="font-size:10px;padding:1px 6px;border-radius:20px;'
                                 'background:#EAF3DE;color:#3B6D11;border:1px solid #97C459;'
                                 'margin-left:6px;">Best</span>') if j == 0 else ""
                    name_style = ("font-size:13px;font-weight:500;color:var(--color-text-primary);"
                                  if j == 0 else "font-size:13px;color:var(--color-text-secondary);")
                    rows_html += (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:6px 0;{border}">'
                        f'  <div style="display:flex;align-items:center;">'
                        f'    <span style="{name_style}">{row["formation_label"]}</span>{pill}'
                        f'  </div>'
                        f'  <div style="display:flex;align-items:center;gap:8px;">'
                        f'    <span style="font-size:11px;color:var(--color-text-tertiary);">{int(row["plays"])} plays</span>'
                        f'    <span style="font-size:13px;font-weight:500;color:{ec};">{row["avg_epa"]:+.3f}</span>'
                        f'  </div>'
                        f'</div>'
                    )
                st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;padding:10px 14px;
            padding-bottom:12px;margin-bottom:4px;
            border-bottom:1px solid var(--color-border-tertiary);">
  <div style="font-size:11px;color:#378ADD;font-weight:500;margin-bottom:6px;">vs {def_form}</div>
  {rows_html}
</div>
""", unsafe_allow_html=True)

        with fvf_right:
            st.markdown(
                '<p style="font-size:11px;color:gray;text-transform:uppercase;'
                'letter-spacing:.08em;margin-bottom:10px;">Top matchups por EPA</p>',
                unsafe_allow_html=True)

            top7      = fvf.head(7)
            rows_html = ""
            for rank, (_, row) in enumerate(top7.iterrows(), start=1):
                ec = "#3B6D11" if row["avg_epa"] >= 0 else "#A32D2D"
                rows_html += (
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:9px 12px;border-bottom:0.5px solid var(--color-border-tertiary);">'
                    f'  <span style="font-size:11px;color:var(--color-text-tertiary);min-width:16px;">{rank}.</span>'
                    f'  <div style="display:flex;flex-direction:column;gap:2px;">'
                    f'    <div style="display:flex;align-items:center;gap:6px;">'
                    f'      <span style="font-size:13px;font-weight:500;color:var(--color-text-primary);">{row["formation_label"]}</span>'
                    f'      <span style="font-size:12px;color:#378ADD;">vs {row["def_formation"]}</span>'
                    f'    </div>'
                    f'    <div style="display:flex;align-items:baseline;gap:6px;">'
                    f'      <span style="font-size:14px;font-weight:500;color:{ec};">{row["avg_epa"]:+.3f}</span>'
                    f'      <span style="font-size:11px;color:var(--color-text-tertiary);">{int(row["plays"])} plays</span>'
                    f'    </div>'
                    f'  </div>'
                    f'</div>'
                )
            st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;overflow:hidden;">
  {rows_html}
</div>
""", unsafe_allow_html=True)


def render_counter_intelligence(filtered_df: pd.DataFrame):
    st.markdown("### 🛡️ Counter Intelligence")
    st.caption("¿Qué cobertura neutraliza mejor el concepto dominante en los datos actuales?")

    if filtered_df.empty:
        st.info("No hay datos suficientes para los filtros actuales.")
        return

    # ── Concepto dominante ────────────────────────────────
    perf = concept_performance(filtered_df)
    if perf.empty:
        st.info("No hay datos suficientes.")
        return

    top_concept = perf.index[0] if "concept" not in perf.columns else perf.iloc[0]["concept"]
    top_epa     = perf.iloc[0]["avg_epa"]

    # ── CVS para ese concepto ─────────────────────────────
    cvs = concept_vs_coverage(filtered_df)
    if cvs.empty:
        st.info("No hay datos de cobertura suficientes.")
        return

    concept_cvs = (
        cvs[cvs["concept"] == top_concept]
        .sort_values("avg_epa", ascending=True)
        .reset_index(drop=True)
    )

    if concept_cvs.empty:
        st.info(f"No hay datos de cobertura para {top_concept}.")
        return

    best_counter    = concept_cvs.iloc[0]
    best_coverage   = best_counter["coverage"]
    best_epa        = best_counter["avg_epa"]

    # ── Insight box ───────────────────────────────────────
    epa_color = "#3B6D11" if best_epa <= 0 else "#BA7517"
    if best_epa <= 0:
        counter_sentence = (
            f'La cobertura que mejor lo neutraliza es'
            f' <span style="color:{epa_color};font-weight:500;">{best_coverage}</span>,'
            f' con EPA ofensivo de'
            f' <span style="color:{epa_color};font-weight:500;">{best_epa:+.3f}</span>.'
        )
    else:
        counter_sentence = (
            f'La cobertura que más lo contiene es'
            f' <span style="color:{epa_color};font-weight:500;">{best_coverage}</span>,'
            f' reduciendo el EPA ofensivo a su mínimo de'
            f' <span style="color:{epa_color};font-weight:500;">{best_epa:+.3f}</span>'
            f' — ninguna cobertura lo neutraliza completamente con los filtros actuales.'
        )
    st.markdown(f"""
<div style="background:var(--color-background-secondary);
            border:0.5px solid var(--color-border-tertiary);
            border-radius:10px;padding:14px 18px;margin-bottom:16px;">
  <p style="font-size:10px;color:gray;text-transform:uppercase;
            letter-spacing:.08em;margin-bottom:6px;">Insight</p>
  <p style="font-size:15px;color:var(--color-text-primary);line-height:1.6;">
    El concepto más eficiente en los datos actuales es
    <span style="color:#378ADD;font-weight:500;">{top_concept}</span>
    (<span style="color:#3B6D11;font-weight:500;">{top_epa:+.3f} EPA</span>).
    {counter_sentence}
  </p>
</div>
""", unsafe_allow_html=True)

    # ── Top 3 cards ───────────────────────────────────────
    top3 = concept_cvs.head(3)
    epa_min   = top3["avg_epa"].min()  # best counter (lowest EPA)
    epa_max   = top3["avg_epa"].max()  # worst counter
    epa_range = epa_max - epa_min if epa_max != epa_min else 1
    cols  = st.columns(3)
    ranks = ["✦ Best counter", "#2", "#3"]

    for i, (col, (_, row)) in enumerate(zip(cols, top3.iterrows())):
        epa_val   = row["avg_epa"]
        epa_color = "#3B6D11" if epa_val <= 0 else "#A32D2D" if epa_val > 0.2 else "#BA7517"
        bar_pct   = max(5, int((epa_max - epa_val) / epa_range * 95))
        bar_color = "#3B6D11" if epa_val <= 0 else "#BA7517" if epa_val < 0.2 else "#A32D2D"
        border    = "border:1px solid #3B6D11;" if i == 0 else ""

        with col:
            st.markdown(f"""
<div style="background:var(--color-background-secondary);
            {border}border-radius:10px;padding:14px 16px;
            border: {'1px solid #3B6D11' if i==0 else '0.5px solid var(--color-border-tertiary)'};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
    <span style="font-size:16px;font-weight:500;color:var(--color-text-primary);">{row['coverage']}</span>
    <span style="font-size:11px;color:{'#3B6D11' if i==0 else 'var(--color-text-tertiary)'};">
      {ranks[i]}</span>
  </div>
  <div style="font-size:12px;color:gray;margin-bottom:10px;">vs {top_concept}</div>
  <div style="font-size:28px;font-weight:500;color:{epa_color};">{epa_val:+.3f}</div>
  <div style="width:100%;height:4px;background:var(--color-border-tertiary);
              border-radius:2px;margin:10px 0;">
    <div style="width:{bar_pct}%;height:100%;background:{bar_color};border-radius:2px;"></div>
  </div>
  <div style="display:flex;gap:12px;">
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Plays</div>
      <div style="font-size:13px;font-weight:500;">{int(row['plays']):,}</div>
    </div>
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Success</div>
      <div style="font-size:13px;font-weight:500;">{row['success_rate']:.1%}</div>
    </div>
    <div>
      <div style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Yards</div>
      <div style="font-size:13px;font-weight:500;">{row['avg_yards']:.1f}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Tabla completa ────────────────────────────────────
    sort_col_ci, _ = st.columns([2, 6])
    with sort_col_ci:
        sort_by = st.selectbox(
            "Sort by", ["Avg EPA ↑", "Most plays", "Success rate ↑"],
            key="ci_sort", label_visibility="collapsed"
        )

    sort_map = {
        "Avg EPA ↑":      ("avg_epa",      True),
        "Most plays":     ("plays",         False),
        "Success rate ↑": ("success_rate",  True),
    }
    sort_col_name, sort_asc = sort_map[sort_by]

    all_cvs = (
        cvs.sort_values(sort_col_name, ascending=sort_asc)
        .reset_index(drop=True)
    )

    # Header
    st.markdown(f"""
<div style="display:grid;grid-template-columns:2fr 2fr 1fr 1.5fr 1fr 1fr;
            border-bottom:0.5px solid var(--color-border-tertiary);
            padding:8px 14px;">
  <span style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Concept</span>
  <span style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Coverage</span>
  <span style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Plays</span>
  <span style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Avg EPA</span>
  <span style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Yards</span>
  <span style="font-size:10px;color:gray;text-transform:uppercase;letter-spacing:.06em;">Success</span>
</div>
""", unsafe_allow_html=True)

    # Rows
    for _, row in all_cvs.iterrows():
        epa_val   = row["avg_epa"]
        epa_color = "#3B6D11" if epa_val <= 0 else "#A32D2D" if epa_val > 0.2 else "var(--color-text-primary)"
        pill      = f"<span style='font-size:10px;padding:2px 7px;border-radius:20px;background:#EAF3DE;color:#3B6D11;border:1px solid #97C459;margin-left:6px;'>Good counter</span>" if epa_val <= 0 else f"<span style='font-size:10px;padding:2px 7px;border-radius:20px;background:#FDE8E8;color:#A32D2D;border:1px solid #F5A0A0;margin-left:6px;'>Weak counter</span>" if epa_val > 0.2 else ""

        st.markdown(f"""
<div style="display:grid;grid-template-columns:2fr 2fr 1fr 1.5fr 1fr 1fr;
            padding:9px 14px;border-bottom:0.5px solid var(--color-border-tertiary);">
  <span style="font-size:13px;font-weight:500;color:var(--color-text-primary);">{row['concept']}</span>
  <span style="font-size:13px;color:#378ADD;">{row['coverage']}</span>
  <span style="font-size:13px;color:var(--color-text-secondary);">{int(row['plays']):,}</span>
  <span style="font-size:13px;font-weight:500;color:{epa_color};">{epa_val:+.3f}{pill}</span>
  <span style="font-size:13px;color:var(--color-text-secondary);">{row['avg_yards']:.1f}</span>
  <span style="font-size:13px;color:var(--color-text-secondary);">{row['success_rate']:.1%}</span>
</div>
""", unsafe_allow_html=True)
