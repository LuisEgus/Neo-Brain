import asyncio
import jwt
import streamlit as st
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.oauth2 import OAuth2Token

# 1. Leer secretos
testing_mode = st.secrets.get("testing_mode", False)
CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
REDIRECT_URL = (
    st.secrets["redirect_url_test"] if testing_mode else st.secrets["redirect_url"]
)

# 2. Cliente OAuth
client = GoogleOAuth2(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# 3. Scopes
SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/calendar.events"
]

def make_auth_url() -> str:
    return asyncio.run(
        client.get_authorization_url(
            redirect_uri=REDIRECT_URL,
            scope=SCOPES,
            extras_params={"access_type": "offline"},
        )
    )

def fetch_token(code: str) -> OAuth2Token:
    return asyncio.run(client.get_access_token(code=code, redirect_uri=REDIRECT_URL))

def decode_user(id_token: str) -> dict:
    return jwt.decode(jwt=id_token, options={"verify_signature": False})

st.set_page_config(page_title="🔐 Login", layout="centered")
st.title("🔐 Login con Google")

# 0) Si ya estamos loggeados, vamos a Home
if "oauth_token" in st.session_state and "user_email" in st.session_state:
    st.success(f"✔️ Ya iniciaste sesión como {st.session_state.user_email}")
    if st.button("Ir a Home"):
        # Redirige a la página principal de tu app (por ejemplo '/')
        js = "window.location.href='/'"
        st.components.v1.html(f"<script>{js}</script>")
    st.stop()

# 1) Si viene con code en URL, hacemos intercambio
params = st.experimental_get_query_params()
if "code" in params:
    code = params["code"][0]
    try:
        token = fetch_token(code)
        info = decode_user(token["id_token"])
        email = info.get("email", "")
        if not email.endswith("@neo.com.pe"):
            st.error("❌ Solo cuentas @neo.com.pe.")
            st.stop()

        # Guardar en sesión
        st.session_state.oauth_token = token
        st.session_state.user_email = email

        # Limpiar params
        st.experimental_set_query_params()

        st.success(f"✔️ Bienvenido {email}")
        st.info("Haz clic en el botón para continuar:")
        if st.button("Continuar"):
            js = "window.location.href='/'"
            st.components.v1.html(f"<script>{js}</script>")
        st.stop()

    except Exception as e:
        st.error(f"Error intercambiando token: {e}")
        st.stop()

# 2) Si no hay code: mostramos botón de login
auth_url = make_auth_url()
st.markdown(
    f"""
    <a href="{auth_url}" target="_self">
        <button style="padding:8px 16px; font-size:16px;">
          🔒 Iniciar sesión con Google (@neo.com.pe)
        </button>
    </a>
    """,
    unsafe_allow_html=True,
)
st.info("Al hacer clic, te redireccionarás a Google para autorizar email y Calendar.")
st.stop()
