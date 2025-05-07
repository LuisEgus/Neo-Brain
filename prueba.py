import streamlit as st
from gcal_client import build_credentials, build_service
import datetime

# 1) Comprueba que ya tienes el token en sesión
if "oauth_token" in st.session_state:
    # 2) Crea credentials de google-auth
    creds = build_credentials(st.session_state.oauth_token)
    # 3) Construye el cliente de Calendar API
    service = build_service(creds)
    # 4) Llama a la API para listar el próximo 1 evento
    events = service.events().list(
        calendarId="primary",
        maxResults=1,
        singleEvents=True,
        orderBy="startTime",
        timeMin=datetime.datetime.utcnow().isoformat() + "Z"
    ).execute()
    # 5) Muestra el resultado en la app
    st.write(events)
