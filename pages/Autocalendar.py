import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import streamlit.components.v1 as components

from gcal_client import build_credentials, build_service, list_events, upsert_event

# ——————————————
# Check de sesión: si no hay token ni email, bloqueamos el acceso
# ——————————————
if "oauth_token" not in st.session_state or "user_email" not in st.session_state:
    st.error("❌ Debes iniciar sesión primero.")
    st.stop()

st.set_page_config(page_title="Neo Brain - Autocalendar", layout="wide")
st.title("Autocalendar")
st.markdown("""
Esta página permite la gestión de reuniones y la asignación de códigos a las mismas.  
Se disponen de dos métodos de asignación:
- **Autorellenado Automático:** Se sugieren códigos para cada reunión; el usuario puede confirmar la propuesta o indicar que no es correcta y asignar otra.
- **Rellenado Manual (por Lotes):** Permite seleccionar varias reuniones y, de forma simultánea, asignar un mismo código.
""")

# ——————————————
# Parámetros de rango de fechas para Calendar
# ——————————————
st.subheader("🔎 Filtrar eventos por rango de fechas")
hoy = datetime.today().date()
fecha_inicio, fecha_fin = st.date_input(
    "Selecciona rango de fechas",
    value=(hoy - timedelta(days=7), hoy + timedelta(days=7)),
    min_value=hoy - timedelta(days=365),
    max_value=hoy + timedelta(days=365),
    help="Puedes elegir fechas pasadas y/o futuras"
)

calendar_id = st.text_input("ID de calendario:", value="primary")
if st.button("Refrescar eventos"):
    st.experimental_rerun()

# Convertir a datetime con hora mínima y máxima
dt_min = datetime.combine(fecha_inicio, time.min)
dt_max = datetime.combine(fecha_fin,   time.max)

# ——————————————
# Traer eventos desde Google Calendar
# ——————————————
creds   = build_credentials(st.session_state.oauth_token)
service = build_service(creds)
events = list_events(
    service,
    calendar_id=calendar_id,
    time_min=dt_min,
    time_max=dt_max
)

# Normalizar eventos en un DataFrame
def normalize_event(ev):
    start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
    end   = ev.get("end",   {}).get("dateTime") or ev.get("end",   {}).get("date")
    return {
        "id":       ev.get("id"),
        "fecha":    pd.to_datetime(start).date(),
        "hora":     pd.to_datetime(start).strftime("%H:%M"),
        "duracion": str(pd.to_datetime(end) - pd.to_datetime(start)),
        "titulo":   ev.get("summary", ""),
        "codigo":   ev.get("description", ""),   # asumimos que 'description' guarda el código
        "detalles": ev.get("description", "")
    }

df_reuniones = pd.DataFrame([normalize_event(e) for e in events])

# ——————————————
# Filtros generales (igual que en el original)
# ——————————————
st.subheader("Filtros Generales")
col1, col2, col3 = st.columns(3)
with col1:
    fi = st.date_input("Fecha inicio", value=df_reuniones["fecha"].min())
with col2:
    ff = st.date_input("Fecha fin",    value=df_reuniones["fecha"].max())
with col3:
    filtro_codigo = st.radio(
        "Filtrar por código",
        ("Todos", "Con código", "Sin código"),
        index=0
    )
filtro_texto = st.text_input("Buscar en título o detalles")

df_filtrado = df_reuniones.copy()
df_filtrado = df_filtrado[(df_filtrado["fecha"] >= fi) & (df_filtrado["fecha"] <= ff)]
if filtro_codigo == "Con código":
    df_filtrado = df_filtrado[df_filtrado["codigo"] != ""]
elif filtro_codigo == "Sin código":
    df_filtrado = df_filtrado[df_filtrado["codigo"] == ""]
if filtro_texto:
    df_filtrado = df_filtrado[
        df_filtrado["titulo"].str.lower().str.contains(filtro_texto.lower()) |
        df_filtrado["detalles"].str.lower().str.contains(filtro_texto.lower())
    ]

# ——————————————
# Tabs internas para asignación de códigos
# ——————————————
tabs = st.tabs(["Autorellenado Automático", "Rellenado Manual (por Lotes)"])

# ------------------------------------------
# Autorellenado Automático
# ------------------------------------------
with tabs[0]:
    st.subheader("Autorellenado Automático")
    st.markdown("Para cada reunión se sugiere un código. Confirma la sugerencia o ingresa otro código si no es correcto.")
    df_auto = df_filtrado.copy()
    for idx, row in df_auto.iterrows():
        st.markdown(f"### {row['titulo']} (ID: {row['id']})")
        st.write(f"**Fecha:** {row['fecha']}  |  **Hora:** {row['hora']}  |  **Duración:** {row['duracion']}")
        codigo_recomendado = f"#1741{row['id'][-4:]}" if isinstance(row['id'], str) else f"#1741{int(row['id']):04d}"
        if row['codigo']:
            st.write(f"**Código asignado:** {row['codigo']}")
        else:
            st.warning("Esta reunión no tiene código asignado.")
            st.info(f"Código recomendado: {codigo_recomendado}")
            opcion = st.radio(
                f"Para la reunión '{row['titulo']}'",
                ["Confirmar recomendado", "No es correcto"],
                key=f"auto_{row['id']}"
            )
            if opcion == "Confirmar recomendado":
                df_auto.at[idx, "codigo"] = codigo_recomendado
                st.success(f"Código actualizado a: {codigo_recomendado}")
            else:
                nuevo_codigo = st.text_input(
                    f"Ingrese otro código para '{row['titulo']}'",
                    key=f"nuevo_auto_{row['id']}"
                )
                if nuevo_codigo:
                    df_auto.at[idx, "codigo"] = nuevo_codigo
                    st.success(f"Código actualizado a: {nuevo_codigo}")
    if st.button("Confirmar cambios en Autorellenado Automático"):
        # Aquí podrías llamar a upsert_event para cada evento modificado
        st.success("Se actualizaron los datos (simulación).")
    st.dataframe(df_auto, use_container_width=True)

# ------------------------------------------
# Rellenado Manual (por Lotes)
# ------------------------------------------
with tabs[1]:
    st.subheader("Rellenado Manual (por Lotes)")
    st.markdown("Selecciona una o varias reuniones y asigna un código en bloque para actualizarlas simultáneamente.")
    df_manual = df_filtrado.copy()
    seleccionados = []
    st.markdown("### Selección de Reuniones")
    for idx, row in df_manual.iterrows():
        c1, c2, c3, c4 = st.columns([0.1, 0.4, 0.3, 0.2])
        with c1:
            sel = st.checkbox("", key=f"check_{row['id']}")
            if sel:
                seleccionados.append(row['id'])
        with c2:
            st.write(f"**{row['titulo']}**")
        with c3:
            st.write(f"{row['fecha']} - {row['hora']}")
        with c4:
            st.write("Código:", row['codigo'] if row['codigo'] else "N/A")
    st.markdown("---")
    st.write(f"Reuniones seleccionadas: {len(seleccionados)}")
    codigo_lote = st.text_input(
        "Ingrese código para aplicar a las reuniones seleccionadas (ej. '#17412081')",
        key="codigo_lote"
    )
    if st.button("Asignar código por lotes"):
        if codigo_lote and seleccionados:
            for idx, row in df_manual.iterrows():
                if row['id'] in seleccionados:
                    df_manual.at[idx, "codigo"] = codigo_lote
            st.success(f"Se asignó el código {codigo_lote} a {len(seleccionados)} reunión(es).")
        elif not codigo_lote:
            st.error("Ingrese un código para asignar.")
        else:
            st.error("No se ha seleccionado ninguna reunión.")
    if st.button("Confirmar cambios en Rellenado Manual"):
        # Aquí podrías llamar a upsert_event en bloque
        st.success("Se actualizaron los datos (simulación).")
    st.dataframe(df_manual, use_container_width=True)
