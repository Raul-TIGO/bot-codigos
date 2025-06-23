# Notebook para generar mensajes técnicos automáticos
# Raul Mendoza - Tigo Panamá

import streamlit as st
import pandas as pd
from datetime import datetime
from urllib.parse import quote
from io import BytesIO
import re

st.set_page_config(page_title="Bot de Códigos Técnicos – Tigo Panamá", layout="wide")

st.title("🤖 Bot de Generación de Códigos Técnicos – Tigo Panamá")
st.markdown("Sube tu archivo Excel (.xlsx) generado desde Microsoft Forms versión **Ver3.0** para generar los códigos automáticamente.")

# Subir archivo Excel
archivo = st.file_uploader("📂 Subir archivo Ver3.0 (.xlsx)", type="xlsx")

if archivo:
    df = pd.read_excel(archivo)

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
        df['Radio'] = df.iloc[:, -1]  # Última columna

    columnas_requeridas = [
        'Carro', 'Nombre del Tecnico', 'Contratista', 'Nombre del cliente',
        'Suscriptor de la Orden', 'Numero De SA', 'Tipo de Escalamiento',
        'Dolor del Cliente', 'Solicitud', 'Razón de Escalamiento', 'Coordenada', 'Radio'
    ]

    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        st.error(f"❌ Faltan columnas en el archivo: {faltantes}")
        st.stop()

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

    def obtener_iniciales(nombre):
        return ''.join([n[0].upper() for n in str(nombre).split()])

    df['InicialesTecnico'] = df['Nombre del Tecnico'].apply(obtener_iniciales)

    if 'Start time' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Start time'])
    else:
        df['Fecha'] = datetime.today()

    df['TipoSolicitud'] = df['Razón de Escalamiento'].apply(clasificar_codigo)
    df = df.sort_values(by='Fecha')
    df['Secuencia'] = df.groupby(['Fecha', 'InicialesTecnico']).cumcount() + 1

    if 'Enviado' not in df.columns:
        df['Enviado'] = False

    mostrar_todos = st.sidebar.checkbox("👁️ Mostrar registros ya enviados", value=False)

    df_filtrado = df if mostrar_todos else df[df['Enviado'] == False]

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

    def limpiar_emojis(texto):
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002700-\U000027BF"
            u"\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', texto)

    def generar_enlace_whatsapp(row, mensaje):
        numero = str(row.get('Radio', '')).replace(" ", "").replace("+", "")
        mensaje_sin_emojis = limpiar_emojis(mensaje)
        mensaje_codificado = quote(mensaje_sin_emojis)
        return f"https://wa.me/507{numero}?text={mensaje_codificado}"

    st.success("✅ Archivo cargado correctamente")

    st.sidebar.header("🧑‍🔧 Generador de Mensaje Individual")
    if len(df_filtrado) == 0:
        st.sidebar.info("✅ Todos los mensajes ya han sido enviados o no hay registros para mostrar.")
    else:
        idx = st.sidebar.selectbox("Selecciona un Técnico", df_filtrado.index, format_func=lambda i: df_filtrado.at[i, 'Nombre del Tecnico'])
        token_manual = st.sidebar.text_input("🔐 Ingresa el Token manual", value="__________")
        mensaje = generar_mensaje(df.loc[idx], token_manual)
        enlace = generar_enlace_whatsapp(df.loc[idx], mensaje)

        st.subheader("📄 Mensaje Generado")
        st.text_area("Puedes copiar este mensaje:", value=mensaje, height=300)
        st.markdown(f"[📲 Abrir WhatsApp con mensaje generado]({enlace})", unsafe_allow_html=True)

        enviado = st.checkbox("✅ Marcar como enviado")
        if enviado:
            df.at[idx, 'Enviado'] = True

    df['MensajeGenerado'] = df.apply(lambda row: generar_mensaje(row), axis=1)
    df['WhatsAppLink'] = df.apply(lambda row: generar_enlace_whatsapp(row, row['MensajeGenerado']), axis=1)

    st.subheader("📋 Vista previa de todos los mensajes")
    click_idx = st.radio("📌 Selecciona un código para ver el mensaje:", df.index, format_func=lambda i: df.at[i, 'CodigoGenerado'], horizontal=True)

    # Actualizar mensaje al hacer clic
    row = df.loc[click_idx]
    token_manual_preview = st.text_input("🔐 Token para este mensaje", value="__________", key="token_preview")
    mensaje_click = generar_mensaje(row, token_manual_preview)
    enlace_click = generar_enlace_whatsapp(row, mensaje_click)

    st.text_area("📩 Mensaje seleccionado:", value=mensaje_click, height=300)
    st.markdown(f"[📲 Abrir WhatsApp con mensaje generado]({enlace_click})", unsafe_allow_html=True)

    st.subheader("📤 Descargar todos los mensajes")
    output = BytesIO()
    df[['Fecha', 'Nombre del Tecnico', 'Radio', 'Suscriptor de la Orden', 'TipoSolicitud', 'CodigoGenerado', 'MensajeGenerado', 'WhatsAppLink', 'Enviado']].to_excel(output, index=False, engine='openpyxl')
    st.download_button(
        label="📥 Descargar Excel con mensajes",
        data=output.getvalue(),
        file_name="Mensajes_Procesados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
