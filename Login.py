import streamlit as st
from google_auth_st import add_auth

# Configuración básica de la página
st.set_page_config(page_title="🔐 Login", layout="centered")

# Mensaje inicial
st.error("🔒 Debes iniciar sesión con Google (@neo.com.pe).")

# Agregar autenticación
add_auth()

# Comprobar si hay email en la sesión
if "email" in st.session_state:
    email = st.session_state.email

    # Validar que el correo sea del dominio @neo.com.pe
    if email.endswith("@neo.com.pe"):
        st.success(f"✔️ Bienvenido {email}")
        
        # Guardar que el usuario está autenticado
        st.session_state.user_email = email
        
        # Redirigir a Home
        st.switch_page("pages/Home.py")  # ⚡ Ajusta el path si tu página Home está en otra ruta
    else:
        st.error("❌ Solo se permiten cuentas @neo.com.pe.")
        # Eliminar email de sesión para forzar nuevo login
        del st.session_state.email

# Si todavía no hay email autenticado
else:
    st.info("Inicia sesión para continuar.")
