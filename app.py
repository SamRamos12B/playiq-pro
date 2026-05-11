import streamlit as st
from auth import require_auth, logout
from paywall import check_and_handle_payment, require_pro
from data.loader import load_data, filter_data
from components.free_dashboard import render_free_filters, render_free_dashboard
from components.dashboard import render_filters, render_explorer, render_analytics

st.set_page_config(
    page_title="PlayIQ Pro",
    page_icon="🏈",
    layout="wide"
)

load_data()  # pre-warm cache before auth gate

user = require_auth()
check_and_handle_payment()

# ── Header ────────────────────────────────────────────────
col1, col2, col3 = st.columns([6, 1, 1])
with col1:
    st.markdown("## 🏈 PlayIQ Pro")
with col2:
    badge = "⭐ Pro" if user["plan"] == "pro" else "🆓 Free"
    st.markdown(f"**{badge}**")
with col3:
    if st.button("Salir", use_container_width=True):
        logout()

if user.get("email") == "samuel.ramos.tr12@gmail.com":
    with st.expander("⚙ Admin", expanded=False):
        st.caption("Cache management")
        if st.button("🗑 Clear data cache", key="admin_clear_cache"):
            st.cache_data.clear()
            st.success("Cache cleared — data will reload on next interaction.")

st.divider()

# ── Cargar datos ──────────────────────────────────────────
df = load_data()

# ═══════════════════════════════════════════════════════════
# FREE TIER
# ═══════════════════════════════════════════════════════════
if user["plan"] != "pro":

    filtros = render_free_filters(df)

    filtered_df = filter_data(
        df,
        teams         = filtros["teams"],
        concepts      = [],
        coverages     = [],
        formation     = "All",
        downs         = [],
        seasons       = filtros["seasons"],
        weeks         = [],
        defteam       = "All",
        def_formation = "All",
    )

    # Filtro de tipo de jugada (local, no en filter_data)
    if filtros["tipo_play"] != "All" and "play_type" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["play_type"] == filtros["tipo_play"]
        ]

    # Layout: dashboard + AI Scout lateral
    col_dash, col_scout = st.columns([3, 1])

    with col_dash:
        render_free_dashboard(filtered_df)

    with col_scout:
        render_ai_scout(filtros, filtered_df)

# ═══════════════════════════════════════════════════════════
# PRO TIER
# ═══════════════════════════════════════════════════════════
else:

    filtros = render_filters(df)

    filtered_df = filter_data(
        df,
        teams         = filtros["teams"],
        concepts      = filtros["concepts"],
        coverages     = filtros["coverages"],
        formation     = filtros["formation"],
        downs         = filtros["downs"],
        seasons       = filtros["seasons"],
        weeks         = filtros["weeks"],
        defteam       = filtros["defteam"],
        def_formation = filtros["def_formation"],
    )

    active = []
    if filtros["teams"]:     active.append(f"Team: {', '.join(filtros['teams'])}")
    if filtros["concepts"]:  active.append(f"Concept: {', '.join(filtros['concepts'])}")
    if filtros["coverages"]: active.append(f"Coverage: {', '.join(filtros['coverages'])}")
    if filtros["downs"]:     active.append(f"Down: {filtros['downs']}")
    if active:
        st.caption("🔎 Active filters: " + " · ".join(active))

    tab_explorer, tab_analytics = st.tabs([
        "🔍 Find a Play",
        "📊 Analytics",
        ])
    
    with tab_explorer:
        render_explorer(filtered_df, df)
        
    with tab_analytics:
        render_analytics(filtered_df, df)
