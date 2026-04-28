from supabase import create_client
import streamlit as st

def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"]
    )

def upgrade_to_pro(user_id: str, stripe_customer_id: str):
    """Actualiza el plan del usuario a pro en Supabase."""
    supabase = get_supabase()
    result = supabase.table("users").update({
        "plan":      "pro",
        "stripe_id": stripe_customer_id
    }).eq("id", user_id).execute()
    return result.data[0] if result.data else None

def get_user(user_id: str):
    """Obtiene el usuario actualizado de Supabase."""
    supabase = get_supabase()
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None