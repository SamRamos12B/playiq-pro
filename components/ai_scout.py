import streamlit as st
import anthropic
from data.context_builder import build_scout_context
from paywall import require_pro

def render_ai_scout(filtros: dict, df):
    """
    Renderiza el panel del AI Scout.
    Recibe los filtros activos y el dataframe del dashboard.
    """
    st.subheader("🤖 AI Scout")

    # Guard de plan
    user = st.session_state.get("user", {})
    is_pro = user.get("plan") == "pro"

    # Mostrar quota para free users
    if not is_pro:
        usage = user.get("scout_usage", 0)
        remaining = max(0, 5 - usage)
        st.caption(f"Consultas disponibles hoy: **{remaining}/5**")
        
        if remaining == 0:
            st.warning("🔒 Alcanzaste tu límite diario. Upgrade a Pro para consultas ilimitadas.")
            require_pro("AI Scout ilimitado")
            return

    # Inicializar historial de chat en session_state
    if "scout_messages" not in st.session_state:
        st.session_state.scout_messages = []

    # Historial con scroll propio
    chat_box = st.container(height=400)
    with chat_box:
        if not st.session_state.scout_messages:
            with st.chat_message("assistant"):
                st.markdown("¡Hola! Soy el AI Scout 🏈 Pregúntame sobre las jugadas que ves en pantalla. Por ejemplo: *¿Qué concepto funciona mejor contra Cover 3?*")
        for msg in st.session_state.scout_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Input fuera del container
    if prompt := st.chat_input("Pregunta sobre las jugadas actuales..."):

        # Verificar quota antes de procesar
        if not is_pro:
            if not _check_and_update_quota(user):
                st.warning("🔒 Sin consultas disponibles. Upgrade a Pro.")
                return

        st.session_state.scout_messages.append({
            "role": "user",
            "content": prompt
        })

        # Spinner y respuesta dentro del mismo chat_box
        with chat_box:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analizando..."):
                    response = _get_scout_response(prompt, filtros, df)
                st.markdown(response)

        st.session_state.scout_messages.append({
            "role": "assistant",
            "content": response
        })
        st.rerun()

    # Botón para limpiar historial
    if st.session_state.scout_messages:
        if st.button("🗑️ Limpiar chat", use_container_width=True):
            st.session_state.scout_messages = []
            st.rerun()

def _get_scout_response(prompt: str, filtros: dict, df) -> str:
    """Llama a Claude con el contexto del dashboard."""
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        system_prompt = build_scout_context(filtros, df)

        # Construir historial para conversación multi-turn
        messages = []
        for msg in st.session_state.scout_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text

    except Exception as e:
        return f"Error al conectar con el Scout: {str(e)}"

def _check_and_update_quota(user: dict) -> bool:
    """
    Verifica y actualiza la quota diaria del usuario free.
    Devuelve True si puede hacer la consulta.
    """
    from supabase import create_client
    from datetime import date

    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

    today = date.today().isoformat()
    usage_date = user.get("usage_date")
    usage = user.get("scout_usage", 0)

    # Si es un día nuevo, resetear contador
    if usage_date != today:
        usage = 0

    if usage >= 5:
        return False

    # Actualizar contador
    result = supabase.table("users").update({
        "scout_usage": usage + 1,
        "usage_date":  today
    }).eq("id", user["id"]).execute()

    # Actualizar sesión local
    st.session_state["user"] = result.data[0]
    return True