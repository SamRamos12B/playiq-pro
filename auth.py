import streamlit as st
from supabase import create_client

def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

def require_auth():
    if not st.user.is_logged_in:
        _render_login_screen()
        st.stop()

    # Upsert en Supabase
    user_email = st.user.email
    user_name  = st.user.name
    user_pic   = st.user.picture

    supabase = get_supabase()
    result = supabase.table("users").upsert({
        "email":      user_email,
        "name":       user_name,
        "avatar_url": user_pic,
    }, on_conflict="email").execute()

    user = result.data[0]
    st.session_state["user"] = user
    return user

def logout():
    st.logout()

def _render_login_screen():
    st.set_page_config(page_title="PlayIQ Pro", page_icon="🏈", layout="centered")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🏈 PlayIQ Pro")
        st.markdown("*NFL Tactical Intelligence*")
        st.divider()
        st.markdown("Analiza jugadas, tendencias y estrategias con IA táctica.")
        st.markdown("")
        if st.button("Continuar con Google", type="primary", use_container_width=True):
            st.login("google")
        st.markdown("")
        st.caption("Free: 5 consultas AI/día · Pro $12/mes: acceso completo")