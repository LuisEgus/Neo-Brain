import re
import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from gcal_client import build_credentials, build_service, list_events, upsert_event

# — Verificación de sesión —
if "oauth_token" not in st.session_state or "user_email" not in st.session_state:
    st.error("❌ Debes iniciar sesión primero.")
    st.stop()

st.set_page_config(page_title="Neo Brain - Autocalendar", layout="wide")
st.title("Autocalendar")

# — Parámetros fijos: descargar todo 2025 —
dt_min = datetime.combine(date(2025, 1, 1), time.min)
dt_max = datetime.combine(date(2025, 12, 31), time.max)
calendar_id = st.text_input("ID de calendario:", value="primary")
if st.button("Recargar año 2025"):
    pass  # fuerza recarga del script

# — Autenticación y descarga de eventos —
creds   = build_credentials(st.session_state.oauth_token)
service = build_service(creds)
events  = list_events(
    service,
    calendar_id=calendar_id,
    time_min=dt_min,
    time_max=dt_max
)

# — Normalizar eventos a DataFrame —
def normalize_event(ev):
    start = ev["start"].get("dateTime") or ev["start"].get("date")
    end   = ev["end"].get("dateTime")   or ev["end"].get("date")
    ds = pd.to_datetime(start)
    de = pd.to_datetime(end)

    title = ev.get("summary", "").strip()
    # Regex para "#12345 – descripción" o "#12345 descripción"
    m = re.match(r"^\#(\d+)(?:\s*[-–—]\s*|\s+)(.*)", title)
    if m:
        code = f"#{m.group(1)}"
        desc = m.group(2).strip()
    else:
        code = ""
        desc = title

    return {
        "id":          ev.get("id"),
        "fecha":       ds.date(),
        "hora":        ds.strftime("%H:%M"),
        "duracion":    str(de - ds),
        "titulo_raw":  title,
        "codigo":      code,
        "descripcion": desc
    }

df_reuniones = pd.DataFrame([normalize_event(e) for e in events])

# — Filtros generales (dentro de 2025) —
st.subheader("📅 Filtros Generales (dentro de 2025)")
col1, col2, col3 = st.columns(3)
with col1:
    fecha_inicio = st.date_input(
        "Fecha inicio",
        value=df_reuniones["fecha"].min(),
        min_value=date(2025,1,1),
        max_value=date(2025,12,31)
    )
with col2:
    fecha_fin = st.date_input(
        "Fecha fin",
        value=df_reuniones["fecha"].max(),
        min_value=date(2025,1,1),
        max_value=date(2025,12,31)
    )
with col3:
    filtro_codigo = st.radio(
        "Filtrar por código",
        ("Todos", "Con código", "Sin código"),
        index=0
    )
filtro_texto = st.text_input("Buscar en título o descripción")

df_filtrado = df_reuniones[
    (df_reuniones["fecha"] >= fecha_inicio) &
    (df_reuniones["fecha"] <= fecha_fin)
].copy()

if filtro_codigo == "Con código":
    df_filtrado = df_filtrado[df_filtrado["codigo"] != ""]
elif filtro_codigo == "Sin código":
    df_filtrado = df_filtrado[df_filtrado["codigo"] == ""]

if filtro_texto:
    txt = filtro_texto.lower()
    df_filtrado = df_filtrado[
        df_filtrado["titulo_raw"].str.lower().str.contains(txt) |
        df_filtrado["descripcion"].str.lower().str.contains(txt)
    ]

# — Pestañas internas: Autorellenado y Manual —
tabs = st.tabs(["Autorellenado Automático", "Rellenado Manual (por Lotes)"])

# --- Autorellenado Automático ---
with tabs[0]:
    st.subheader("Autorellenado Automático")
    df_auto = df_filtrado.copy()
    for idx, row in df_auto.iterrows():
        st.markdown(f"### {row['titulo_raw']}  (ID: {row['id']})")
        st.write(f"**Fecha:** {row['fecha']}    |    **Hora:** {row['hora']}    |    **Duración:** {row['duracion']}")
        if row["codigo"]:
            st.write(f"**Código actual:** {row['codigo']}")
            nuevo_codigo = row["codigo"]
        else:
            recomend = f"#1741{row['id'][-4:]}"
            st.warning("Sin código asignado.")
            st.info(f"Código sugerido: {recomend}")
            opcion = st.radio(
                f"Para reunión {row['id']}:",
                ["Confirmar sugerido", "Ingresar otro"],
                key=f"auto_{row['id']}"
            )
            if opcion == "Confirmar sugerido":
                nuevo_codigo = recomend
            else:
                nuevo_codigo = st.text_input(
                    "Nuevo código:",
                    key=f"nuevo_{row['id']}"
                )
        if nuevo_codigo and nuevo_codigo != row["codigo"]:
            # 1) Actualizar en Google Calendar
            nuevo_titulo = f"{nuevo_codigo} – {row['descripcion'] or row['titulo_raw']}"
            upsert_event(
                service=service,
                calendar_id=calendar_id,
                event_id=row["id"],
                summary=nuevo_titulo
            )
            # 2) Reflejar en DataFrame
            df_auto.at[idx, "codigo"]     = nuevo_codigo
            df_auto.at[idx, "titulo_raw"] = nuevo_titulo
            st.success(f"Evento actualizado: {nuevo_titulo}")

    st.dataframe(df_auto, use_container_width=True)

# --- Rellenado Manual (por Lotes) ---
with tabs[1]:
    st.subheader("Rellenado Manual (por Lotes)")
    df_manual = df_filtrado.copy()
    seleccionados = []
    for idx, row in df_manual.iterrows():
        c1, c2, c3, c4 = st.columns([0.1, 0.4, 0.3, 0.2])
        with c1:
            sel = st.checkbox("", key=f"chk_{row['id']}")
            if sel:
                seleccionados.append(row["id"])
        with c2:
            st.write(row["titulo_raw"])
        with c3:
            st.write(f"{row['fecha']} {row['hora']}")
        with c4:
            st.write("Código:", row["codigo"] or "N/A")

    st.write(f"Reuniones seleccionadas: {len(seleccionados)}")
    codigo_lote = st.text_input("Código para lote", key="cod_lote")
    if st.button("Asignar lote"):
        if not codigo_lote:
            st.error("Ingresa un código.")
        elif not seleccionados:
            st.error("Selecciona al menos una reunión.")
        else:
            for idx, row in df_manual.iterrows():
                if row["id"] in seleccionados:
                    nuevo_titulo = f"{codigo_lote} – {row['descripcion'] or row['titulo_raw']}"
                    # Actualizar en Google Calendar
                    upsert_event(
                        service=service,
                        calendar_id=calendar_id,
                        event_id=row["id"],
                        summary=nuevo_titulo
                    )
                    # Reflejar localmente
                    df_manual.at[idx, "codigo"]     = codigo_lote
                    df_manual.at[idx, "titulo_raw"] = nuevo_titulo
            st.success(f"Código {codigo_lote} asignado a {len(seleccionados)} reunión(es).")

    st.dataframe(df_manual, use_container_width=True)
