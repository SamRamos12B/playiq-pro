import stripe
import streamlit as st

def get_stripe():
    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
    return stripe

def create_checkout_session(user_email: str, user_id: str) -> str:
    s = get_stripe()

    base_url = st.secrets.get("APP_URL", "http://localhost:8501")

    session = s.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": st.secrets["STRIPE_PRICE_ID"],
            "quantity": 1,
        }],
        mode="subscription",
        customer_email=user_email,
        client_reference_id=user_id,
        success_url=f"{base_url}/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/",
    )
    return session.url

def verify_payment(session_id: str) -> dict | None:
    """
    Verifica si un checkout session fue pagado.
    Devuelve los datos del customer o None si no está pagado.
    """
    s = get_stripe()
    
    try:
        session = s.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            return {
                "stripe_customer_id": session.customer,
                "user_id": session.client_reference_id
            }
    except Exception:
        pass
    return None