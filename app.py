import streamlit as st
import pandas as pd
from datetime import datetime
from urllib.parse import quote
from io import BytesIO

st.set_page_config(page_title="Bot de Códigos Técnicos – Tigo Panamá", layout="wide")
st.title("🤖 Bot de Generación de Códigos Técnicos – Tigo Panamá")
st.markdown("Sube tu archivo Excel (.xlsx) generado desde Microsoft Forms versión **Ver3.0** para generar los códigos automáticamente.")

# 📂 Subida del archivo
archivo = st.file_uploader("📂 Subir archivo Ver3.0 (.xlsx)", type="xlsx")

if archivo:
    df = pd.read_excel(archivo)

    # Revisión de columnas base por posición si no tienen nombre
    if 'Nombre del cliente' not in df.columns:
        df['Nombre del cliente'] = df.iloc[:, 10]  # Columna K
    if 'Diagnóstico' not in df.columns:
        df['Diagnóstico'] = df.iloc[:, 11]  # Columna L
    if 'Tipo de Escalamiento' not in df.columns:
        df['Tipo de Escalamiento'] = df.iloc[:, 17]  # Columna R
    if 'Razón de Escalamiento' not in df.columns:
        df['Razón de Escalamiento'] = df.apply(
            lambda row: row.iloc[20] if pd.notna(row.iloc[20]) else row.iloc[19], axis=1
        )
    if 'Radio' not in df.columns:
        df['Radio'] = df.iloc[:, -1]

    # Validación de columnas mínimas
    columnas_requeridas = [
        'Carro', 'Nombre del Tecnico', 'Contratista', 'Nombre del cliente',
        'Suscriptor de la Orden', 'Numero De SA', 'Tipo de Escalamiento',
        'Dolor del Cliente', 'Solicitud', 'Razón de Escalamiento', 'Coordenada', 'Radio'
    ]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        st.error(f"❌ Faltan columnas en el archivo: {faltantes}")
        st.stop()

    # Función para clasificar por tipo de solicitud
    def clasificar_codigo(diagnostico):
        diag = str(diagnostico).lower()
        if "nap lleno" in diag or "tap lleno" in diag:
            return "TAP/NAP"
        elif any(p in diag for p in ["nivel", "reversa", "mer", "ber", "snr", "hum", "tap", "sin señal", "poste", "fibra"]):
            return "MCO"
        elif "cable" in diag or "acometida" in diag or "drop" in diag:
            return "Recableado"
        else:
            return "Otro"

    # Función para obtener iniciales del técnico
    def obtener_iniciales(nombre):
        return ''.join([n[0].upper() for n in str(nombre).split()])

    # Obtener iniciales
    df['InicialesTecnico'] = df['Nombre del Tecnico'].apply(obtener_iniciales)

    # Fecha
    if 'Start time' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Start time'])
    else:
        df['Fecha'] = datetime.today()

    # Clasificar solicitud
    df['TipoSolicitud'] = df['Razón de Escalamiento'].apply(clasificar_codigo)

    # Generar secuencia por técnico por día
    df = df.sort_values(by='Fecha')
    df['Secuencia'] = df.groupby(['Fecha', 'InicialesTecnico']).cumcount() + 1

    # Función para generar código técnico
    def generar_codigo(tipo, fecha, tecnico, secuencia):
        fecha = pd.to_datetime(fecha)
        suma = fecha.day + fecha.month
        inicial_mes = fecha.strftime('%b')[0].upper()
        iniciales_tecnico = obtener_iniciales(tecnico)
        base = f"{suma:02d}{inicial_mes}{iniciales_tecnico}{secuencia}"
        if tipo == "MCO":
            return f"C4130{base}"
        elif tipo == "Recableado":
            return f"RC4130{base}"
        elif tipo == "TAP/NAP":
            return f"4139{base}"
        else:
            return f"CODIGO{base}"

    df['CodigoGenerado'] = df.apply(
        lambda row: generar_codigo(row['TipoSolicitud'], row['Fecha'], row['Nombre del Tecnico'], row['Secuencia']),
        axis=1
    )

    # Función para generar mensaje
    def generar_mensaje(row, token="__________"):
        return f"""🚐 # de Carro: {row.get('Carro', '')}
👷Tecnico: {row.get('Nombre del Tecnico', '')} 
📲Contratista: {row.get('Contratista', '')}
📞Radio del Técnico: {row.get('Radio', '')}
👤Nombre del cliente: {row.get('Nombre del cliente', '')}
✏️Numero de Suscriptor: {row.get('Suscriptor de la Orden', '')}
🌐Numero de SA: {row.get('Numero De SA', '')}
📝Tipo de Orden: 
🚑Dolor del Cliente: {row.get('Dolor del Cliente', '')}
📩Solicitud: {row.get('Solicitud', '')}
🛰️Diagnóstico: {row.get('Diagnóstico', '')}
📍Coordenada: {row.get('Coordenada', '')}
🔐Token: {token}
🧾 Código Técnico: {row['CodigoGenerado']}
⚠️ *Recuerda ingresar el Token antes de enviar*"""

    def generar_enlace_whatsapp(row, mensaje):
        numero = str(row.get('Radio', '')).replace(" ", "").replace("+", "")
        mensaje_codificado = quote(mensaje)
        return f"https://wa.me/507{numero}?text={mensaje_codificado}"

    st.success("✅ Archivo cargado correctamente")

    # Sidebar para seleccionar fila
    st.sidebar.header("🧑‍🔧 Generador de Mensaje Individual")
    idx = st.sidebar.selectbox("Selecciona un Técnico", df.index, format_func=lambda i: df.at[i, 'Nombre del Tecnico'])
    token_manual = st.sidebar.text_input("🔐 Ingresa el Token manual", value="__________")

    # Mensaje individual
    mensaje = generar_mensaje(df.loc[idx], token_manual)
    enlace = generar_enlace_whatsapp(df.loc[idx], mensaje)

    st.subheader("📄 Mensaje Generado")
    st.text_area("Puedes copiar este mensaje:", value=mensaje, height=300)
    st.markdown(f"[📲 Abrir WhatsApp con mensaje generado]({enlace})", unsafe_allow_html=True)

    # Mensajes masivos
    df['MensajeGenerado'] = df.apply(lambda row: generar_mensaje(row), axis=1)
    df['WhatsAppLink'] = df.apply(lambda row: generar_enlace_whatsapp(row, row['MensajeGenerado']), axis=1)

    st.subheader("📋 Todos los mensajes generados")
    st.dataframe(df[['Fecha', 'Nombre del Tecnico', 'TipoSolicitud', 'CodigoGenerado', 'MensajeGenerado', 'WhatsAppLink']])

    # Exportar
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    st.subheader("📤 Descargar todos los mensajes")
    st.download_button(
        label="⬇️ Descargar Excel con resultados",
        data=output,
        file_name="Mensajes_Procesados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
