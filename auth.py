import streamlit as st
from google_auth_oauthlib.flow import Flow
from supabase import create_client
import requests
import secrets
import hashlib
import base64

# ── Clientes ────────────────────────────────────────────
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

def get_google_flow():
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id":     st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [st.secrets["REDIRECT_URI"]],
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
            }
        },
        # ← Cambia a URLs completas
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_uri=st.secrets["REDIRECT_URI"]
    )

# ── PKCE helpers ─────────────────────────────────────────
def _generate_code_verifier():
    return secrets.token_urlsafe(32)

def _generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

# ── Login ────────────────────────────────────────────────
def login():
    flow = get_google_flow()
    
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)

    # Preservar session_id de Stripe si existe
    stripe_session = st.query_params.get("session_id", "")
    
    # Empacar verifier + stripe_session en state
    state_value = f"{code_verifier}|{stripe_session}"

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        code_challenge=code_challenge,
        code_challenge_method="S256",
        state=state_value
    )
    st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', 
                unsafe_allow_html=True)
    st.stop()

# ── Callback ─────────────────────────────────────────────
def handle_callback(code: str):
    flow = get_google_flow()
    
    # Desempacar verifier + stripe_session del state
    raw_state = st.query_params.get("state", "|")
    parts = raw_state.split("|", 1)
    code_verifier = parts[0]
    stripe_session_id = parts[1] if len(parts) > 1 else ""

    import os
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    flow.fetch_token(code=code, code_verifier=code_verifier)

    credentials = flow.credentials
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    ).json()

    supabase = get_supabase()
    result = supabase.table("users").upsert({
        "email":      userinfo["email"],
        "name":       userinfo.get("name"),
        "avatar_url": userinfo.get("picture"),
    }, on_conflict="email").execute()

    st.session_state["user"] = result.data[0]
    st.query_params.clear()
    
    # Restaurar session_id de Stripe si existía
    if stripe_session_id:
        st.query_params["session_id"] = stripe_session_id

# ── Logout ───────────────────────────────────────────────
def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("code_verifier", None)
    st.rerun()

# ── Guard ────────────────────────────────────────────────
def require_auth():
    params = st.query_params

    if "code" in params and "user" not in st.session_state:
        handle_callback(params["code"])
        st.rerun()

    if "user" not in st.session_state:
        _render_login_screen()
        st.stop()

    return st.session_state["user"]

# ── UI de login ──────────────────────────────────────────
def _render_login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🏈 PlayIQ Pro")
        st.markdown("*NFL Tactical Intelligence*")
        st.divider()
        st.markdown("Analiza jugadas, tendencias y estrategias con IA táctica.")
        st.markdown("")
        if st.button("Continuar con Google", type="primary", use_container_width=True):
            login()
        st.markdown("")
        st.caption("Free: 5 consultas AI/día · Pro $12/mes: acceso completo")