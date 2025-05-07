import streamlit as st
import streamlit.components.v1 as components

# Check de sesión: si no hay token ni email, bloqueamos el acceso
if "oauth_token" not in st.session_state or "user_email" not in st.session_state:
    st.error("❌ Debes iniciar sesión primero.")
    st.stop()

st.set_page_config(page_title="Neo Brain - Chatbot", layout="wide")

st.title("Chatbot")
st.markdown("""
Área para interactuar con el chatbot.  
Actualmente se muestra un ejemplo utilizando un iframe de Dialogflow.  
Reemplaza la URL por la de tu agente en producción.
""")
dialogflow_url = "https://console.dialogflow.com/api-client/demo/embedded/your-dialogflow-agent"
components.html(
    f"""
    <iframe src="{dialogflow_url}" width="100%" height="600" frameborder="0"></iframe>
    """,
    height=600,
)
