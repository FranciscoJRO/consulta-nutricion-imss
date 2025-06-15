import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import io

# --- Conexión a base de datos ---
conn = sqlite3.connect('pacientes.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nss TEXT NOT NULL,
    tipo TEXT NOT NULL,
    nota TEXT,
    fecha TEXT
)
''')
conn.commit()

# --- Título ---
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

    /* Botones */
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

    /* FORZAR TEXTO NEGRO EN RADIO BUTTONS - SELECTORES MÁS AGRESIVOS */
    .stRadio * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    .stRadio > div {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    .stRadio > div > div {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    .stRadio > div > div > label {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    .stRadio label {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Contenedor principal de radio buttons */
    div[role='radiogroup'] {
        color: #000000 !important;
    }
    
    div[role='radiogroup'] * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Cada opción individual */
    div[role='radiogroup'] > div {
        color: #000000 !important;
    }
    
    /* Labels específicos de cada radio button */
    div[role='radiogroup'] > div > label {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Todos los elementos dentro del radiogroup */
    div[role='radiogroup'] > div > label * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Texto dentro de los spans */
    div[role='radiogroup'] > div > label > div > span {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Para asegurar que todos los elementos span tengan color negro */
    div[data-baseweb="radio"] {
        color: #000000 !important;
    }
    
    div[data-baseweb="radio"] * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    div[data-baseweb="radio"] span {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Selector más específico para el texto de las opciones */
    .stRadio label span {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    .stRadio span {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Selectores súper específicos */
    [data-testid="stRadio"] {
        color: #000000 !important;
    }
    
    [data-testid="stRadio"] * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stRadio"] label {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stRadio"] span {
        color: #000000 !important;
        font-weight: 600 !important;
    }

    /* Estilo para mensajes tipo st.info, st.warning, etc. */
    .stAlert {
        background-color: #f8d8e8 !important;
        border: 1px solid #f06292;
        color: #333333 !important;
        font-weight: 500;
    }
    .stAlert > div {
        color: #333333 !important;
    }
    </style>
""", unsafe_allow_html=True)


# --- Registro de paciente ---
tipo = st.radio("Tipo de paciente", ["Nuevo", "Subsecuente"])
nombre = st.text_input("Nombre del paciente")
nss = st.text_input("Número de Seguridad Social (NSS)")
nota = st.text_area("Nota de la consulta")

if st.button("Guardar consulta"):
    if not nombre.strip() or not nss.strip():
        st.warning("Por favor, ingresa el nombre y NSS del paciente.")
    else:
        fecha = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO pacientes (nombre, nss, tipo, nota, fecha)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, nss, tipo, nota, fecha))
        conn.commit()
        st.success("Consulta guardada correctamente.")

# --- Resumen del día ---
st.subheader("Resumen de pacientes de hoy")
hoy = datetime.now().strftime("%Y-%m-%d")
cursor.execute("SELECT nombre, nss, tipo, nota, fecha FROM pacientes WHERE fecha = ?", (hoy,))
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
else:
    st.info("Aún no hay pacientes registrados hoy.")

# --- Buscar por NSS ---
st.subheader("🔍 Buscar paciente por NSS")
buscar_nss = st.text_input("Escribe el NSS a buscar")

if buscar_nss.strip():
    cursor.execute("SELECT nombre, tipo, nota, fecha FROM pacientes WHERE nss = ?", (buscar_nss,))
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
    cursor.execute("SELECT nombre, nss, tipo, nota FROM pacientes WHERE fecha = ?", (fecha_str,))
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