import streamlit as st
import psycopg2
from datetime import datetime
import pandas as pd
import io
from PIL import Image
import re
import os
import requests
import base64

# --- Función OCR con API OCR.space ---
def extraer_texto_con_ocr_space(imagen_stream):
    api_key = os.environ["OCR_API_KEY"]
    url_api = "https://api.ocr.space/parse/image"

    image_data = imagen_stream.read()
    encoded_image = base64.b64encode(image_data).decode()

    payload = {
        'apikey': api_key,
        'language': 'spa',
        'isOverlayRequired': False,
        'base64Image': f'data:image/jpeg;base64,{encoded_image}',
    }

    response = requests.post(url_api, data=payload)
    result = response.json()

    if result.get("IsErroredOnProcessing"):
        raise Exception(result.get("ErrorMessage", ["Error desconocido"])[0])

    parsed_results = result.get("ParsedResults")
    if parsed_results:
        return parsed_results[0]["ParsedText"]
    else:
        return ""

# --- Conexión a base de datos PostgreSQL ---
conn = psycopg2.connect(
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=os.environ["DB_PORT"]
)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS pacientes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    nss TEXT NOT NULL,
    tipo TEXT NOT NULL,
    nota TEXT,
    fecha TEXT
)
''')
conn.commit()

# --- Título e interfaz ---
st.title("Registro de Pacientes - Consulta Nutrición IMSS")

st.markdown("""
<style>
    .stApp {
        background-color: #ffe6f0;
        color: #222222;
    }
    h1, h2, h3, h4 {
        color: #cc0066 !important;
    }
    label, .stTextInput > label, .stTextArea > label, .stDateInput > label {
        color: #222222 !important;
        font-weight: 600;
    }
    .stDownloadButton > button, .stButton > button {
        background-color: #cc0066;
        color: white !important;
        border-radius: 8px;
        font-weight: bold;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #b30059;
        color: white !important;
    }
    input, textarea {
        background-color: white !important;
        color: #000000 !important;
    }
    .stRadio * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# OCR desde carnet
st.subheader("📷 Captura desde carnet del IMSS")

imagen = st.file_uploader("Toma o sube una foto del carnet", type=["png", "jpg", "jpeg"])
nombre_extraido = ""
nss_extraido = ""

if imagen:
    try:
        texto = extraer_texto_con_ocr_space(imagen)
        st.text_area("🧾 Texto detectado", texto, height=300)

        nombre_match = re.search(r'NOMBRE:\s*(.*?)\n(.*?)\n', texto)
        if nombre_match:
            nombre_extraido = f"{nombre_match.group(1).strip()} {nombre_match.group(2).strip()}"
            st.success(f"✅ Nombre detectado: {nombre_extraido}")

        texto_limpio = texto.replace(" ", "").replace("-", "").replace("\n", "")
        posibles_nss = re.findall(r'\d{11}', texto_limpio)

        if posibles_nss:
            nss_extraido = posibles_nss[0]
            st.success(f"✅ NSS detectado: {nss_extraido}")
        else:
            for linea in texto.split("\n"):
                if re.search(r'seg.*social', linea, re.IGNORECASE):
                    digitos = re.findall(r'\d', linea)
                    if len(digitos) >= 11:
                        nss_extraido = ''.join(digitos[:11])
                        st.success(f"✅ NSS detectado por línea: {nss_extraido}")
                        break
    except Exception as e:
        st.error(f"❌ Error en OCR: {e}")
        st.info("💡 Puedes ingresar manualmente los datos del paciente abajo")

# Registro de paciente
tipo = st.radio("Tipo de paciente", ["Nuevo", "Subsecuente"])
nombre = st.text_input("Nombre del paciente", value=nombre_extraido)
nss = st.text_input("Número de Seguridad Social (NSS)", value=nss_extraido)
nota = st.text_area("Nota de la consulta")

if st.button("Guardar consulta"):
    if not nombre.strip() or not nss.strip():
        st.warning("Por favor, ingresa el nombre y NSS del paciente.")
    else:
        fecha = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO pacientes (nombre, nss, tipo, nota, fecha)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, nss, tipo, nota, fecha))
        conn.commit()
        st.success("Consulta guardada correctamente.")
        st.rerun()

# --- Resumen del día ---
st.subheader("Resumen de pacientes de hoy")
hoy = datetime.now().strftime("%Y-%m-%d")
cursor.execute("""
    SELECT nombre, nss, tipo, nota, fecha FROM pacientes 
    WHERE TO_DATE(fecha, 'YYYY-MM-DD') >= CURRENT_DATE - INTERVAL '3 days'
    ORDER BY TO_DATE(fecha, 'YYYY-MM-DD') DESC
""")

datos = cursor.fetchall()

if datos:
    for paciente in datos:
        st.markdown(f"""🧾 **{paciente[0]}**  
        NSS: `{paciente[1]}`  
        Tipo: **{paciente[2]}**  
        Nota: _{paciente[3]}_  
        ---""")

    df = pd.DataFrame(datos, columns=["Nombre", "NSS", "Tipo", "Nota", "Fecha"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Exportar resumen en Excel",
        data=excel_data,
        file_name=f"resumen_pacientes_{hoy}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.markdown("""
    <div style="position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #fff3cd; color: #856404;
        padding: 12px; border-top: 2px solid #ffeeba;
        font-weight: bold; text-align: center; z-index: 1000;">
    ⚠️ Antes de cerrar esta página, recuerda descargar el resumen de pacientes con el botón 📥 **Exportar resumen en Excel**.
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("Aún no hay pacientes registrados hoy.")

# --- Buscar por NSS ---
st.subheader("🔍 Buscar paciente por NSS")
buscar_nss = st.text_input("Escribe el NSS a buscar")

if buscar_nss.strip():
    cursor.execute("SELECT nombre, tipo, nota, fecha FROM pacientes WHERE nss = %s", (buscar_nss,))
    resultados = cursor.fetchall()
    if resultados:
        for r in resultados:
            st.markdown(f"""👤 **{r[0]}**  
            Tipo: {r[1]}  
            Nota: _{r[2]}_  
            Fecha: {r[3]}  
            ---""")
    else:
        st.warning("No se encontró ningún paciente con ese NSS.")

# --- Historial por fecha ---
st.subheader("📅 Ver historial por fecha")
fecha_busqueda = st.date_input("Selecciona una fecha", value=datetime.now())
fecha_str = fecha_busqueda.strftime("%Y-%m-%d")

if st.button("Ver historial de esa fecha"):
    cursor.execute("SELECT nombre, nss, tipo, nota FROM pacientes WHERE fecha = %s", (fecha_str,))
    historial = cursor.fetchall()
    if historial:
        st.markdown(f"### Pacientes del {fecha_str}")
        for p in historial:
            st.markdown(f"""🧾 **{p[0]}**  
            NSS: `{p[1]}`  
            Tipo: {p[2]}  
            Nota: _{p[3]}_  
            ---""")
    else:
        st.info("No hay registros para esa fecha.")

# --- Cerrar conexión ---
conn.close()

