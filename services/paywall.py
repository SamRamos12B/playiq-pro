import streamlit as st
from services.stripe_service import create_checkout_session, verify_payment
from services.supabase_service import upgrade_to_pro, get_user

def check_and_handle_payment():
    params = st.query_params
    
    if "session_id" in params and st.session_state["user"]["plan"] == "free":
        session_id = params["session_id"]
        payment = verify_payment(session_id)
        
        if payment:
            updated_user = upgrade_to_pro(
                payment["user_id"],
                payment["stripe_customer_id"]
            )
            st.session_state["user"] = updated_user
            st.query_params.clear()
            st.success("🎉 ¡Bienvenido a PlayIQ Pro!")
            st.rerun()

def require_pro(feature_name: str = "esta función"):
    user = st.session_state.get("user", {})
    
    if user.get("plan") != "pro":
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning(f"🔒 **{feature_name}** es exclusivo de PlayIQ Pro")
            st.caption("Acceso completo por $12/mes · Cancela cuando quieras")
        with col2:
            if st.button("⭐ Upgrade a Pro", type="primary", use_container_width=True):
                url = create_checkout_session(
                    user["email"],
                    user["id"]
                )
                st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">',
                           unsafe_allow_html=True)
                st.stop()
        st.stop()