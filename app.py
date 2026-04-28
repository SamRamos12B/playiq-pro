import streamlit as st
import pandas as pd
from auth import require_auth, logout
from paywall import check_and_handle_payment, require_pro
from components.ai_scout import render_ai_scout

st.set_page_config(
    page_title="PlayIQ Pro",
    page_icon="🏈",
    layout="wide"
)

user = require_auth()
check_and_handle_payment()

# Header
col1, col2, col3 = st.columns([6, 1, 1])
with col1:
    st.markdown("## 🏈 PlayIQ Pro")
with col2:
    plan_badge = "⭐ Pro" if user["plan"] == "pro" else "🆓 Free"
    st.markdown(f"**{plan_badge}**")
with col3:
    if st.button("Salir", use_container_width=True):
        logout()

st.divider()

# Layout: dashboard izquierda, scout derecha
col_dashboard, col_scout = st.columns([3, 1])

with col_dashboard:
    st.subheader("📊 Dashboard")

    # ── Filtros ──────────────────────────────────────────
    # Aquí van tus filtros actuales de PlayIQ
    # Por ahora usamos valores de ejemplo
    filtros = {
        "equipo":    st.selectbox("Equipo", ["KC", "SF", "DAL", "BUF"]),
        "temporada": st.selectbox("Temporada", [2024, 2023, 2022]),
        "semanas":   st.slider("Semanas", 1, 18, (1, 18)),
        "tipo_play": st.selectbox("Tipo de jugada", ["Todas", "pass", "run"])
    }

    # ── Datos de ejemplo hasta conectar nfl-data-py ──────
    # Reemplaza esto con tu loader real en el Día 4
    df = pd.DataFrame({
        "play_type":    ["pass", "run", "pass", "run", "pass"] * 20,
        "yards_gained": [7, 3, 12, 1, -2] * 20,
        "epa":          [0.3, -0.1, 0.8, -0.4, -0.2] * 20,
        "down":         [1, 2, 3, 1, 2] * 20,
        "ydstogo":      [10, 7, 5, 10, 8] * 20,
    })

    st.dataframe(df.head(20), use_container_width=True)

with col_scout:
    render_ai_scout(filtros, df)