import streamlit as st
from auth import require_auth, logout
from paywall import check_and_handle_payment
from components.dashboard import render_filters, render_dashboard
from components.ai_scout import render_ai_scout

st.set_page_config(
    page_title="PlayIQ Pro",
    page_icon="🏈",
    layout="wide"
)

user = require_auth()
check_and_handle_payment()

# ── Header ───────────────────────────────────────────────
col1, col2, col3 = st.columns([6, 1, 1])
with col1:
    st.markdown("## 🏈 PlayIQ Pro")
with col2:
    badge = "⭐ Pro" if user["plan"] == "pro" else "🆓 Free"
    st.markdown(f"**{badge}**")
with col3:
    if st.button("Salir", use_container_width=True):
        logout()

st.divider()

# ── Filtros en sidebar ───────────────────────────────────
filtros = render_filters()

# ── Layout principal ─────────────────────────────────────
col_dash, col_scout = st.columns([3, 1])

with col_dash:
    df = render_dashboard(filtros)

with col_scout:
    render_ai_scout(filtros, df)