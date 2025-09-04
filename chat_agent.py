import streamlit as st
import pandas as pd
from database_agent import DatabaseAgent
import json

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="🤖 Agente de Consultas de Inventario",
    page_icon="🤖",
    layout="wide",
)

# --- INICIALIZAR EL AGENTE ---
@st.cache_resource
def initialize_agent():
    return DatabaseAgent()

# --- FUNCIONES AUXILIARES ---
def display_results(response):
    """Mostrar resultados de manera organizada"""
    if "error" in response and response["error"]:
        st.error(f"❌ {response['error']}")
        return
    
    # Mostrar interpretación del agente
    st.success("🤖 **Respuesta del Agente:**")
    st.write(response['interpretation'])
    
    # Mostrar datos en tabla si hay resultados
    if response['results'] and len(response['results']) > 0:
        st.subheader(f"📊 Datos encontrados ({response['count']} registros)")
        df = pd.DataFrame(response['results'])
        st.dataframe(df, use_container_width=True)
        
        # Opción para descargar datos
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar datos como CSV",
            data=csv,
            file_name="consulta_inventario.csv",
            mime="text/csv"
        )
    
    # Mostrar consulta SQL generada (opcional)
    with st.expander("🔍 Ver consulta SQL generada"):
        st.code(response['sql'], language='sql')

# --- APLICACIÓN PRINCIPAL ---
st.title("🤖 Agente Inteligente de Consultas de Inventario")
st.subheader("Powered by Gemini 2.5 Pro")

# Inicializar el agente
try:
    agent = initialize_agent()
    st.success("✅ Agente inicializado correctamente")
except Exception as e:
    st.error(f"❌ Error inicializando agente: {e}")
    st.stop()

# --- INTERFAZ DE CHAT ---
st.header("💬 Haz tu consulta")

# Inicializar historial de chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Ejemplos de preguntas sugeridas
st.subheader("💡 Preguntas sugeridas:")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔍 ¿Qué productos tengo en stock?"):
        question = "¿Qué productos tengo en stock?"
        st.session_state.current_question = question

with col2:
    if st.button("⚠️ ¿Cuáles tienen stock bajo?"):
        question = "¿Qué productos tienen stock menor a 50 unidades?"
        st.session_state.current_question = question

with col3:
    if st.button("📅 ¿Qué productos vencen pronto?"):
        question = "¿Qué productos vencen en los próximos 30 días?"
        st.session_state.current_question = question

# Más preguntas sugeridas
col4, col5, col6 = st.columns(3)

with col4:
    if st.button("🏦 ¿Productos por proveedor?"):
        question = "¿Cuántos productos tengo de cada proveedor?"
        st.session_state.current_question = question

with col5:
    if st.button("📦 ¿Productos por categoría?"):
        question = "¿Cómo se distribuyen mis productos por categoría?"
        st.session_state.current_question = question

with col6:
    if st.button("💰 ¿Productos más caros?"):
        question = "¿Cuáles son los 10 productos más caros?"
        st.session_state.current_question = question

# Input de texto para preguntas personalizadas
question_input = st.text_input(
    "✍️ O escribe tu propia pregunta:",
    value=st.session_state.get('current_question', ''),
    placeholder="Ejemplo: ¿Cuántos kilos de arroz tengo en stock?",
    help="Haz preguntas naturales sobre tu inventario. El agente las convertirá en consultas SQL automáticamente."
)

# Botón para procesar la pregunta
if st.button("🚀 Consultar", type="primary") or st.session_state.get('current_question'):
    question = question_input or st.session_state.get('current_question', '')
    
    if question:
        # Limpiar current_question después de usar
        if 'current_question' in st.session_state:
            del st.session_state.current_question
        
        # Agregar pregunta al historial
        st.session_state.chat_history.append({"type": "question", "content": question})
        
        with st.spinner("🤖 El agente está procesando tu consulta..."):
            # Obtener respuesta del agente
            response = agent.ask(question)
            
            # Agregar respuesta al historial
            st.session_state.chat_history.append({"type": "response", "content": response})
            
            # Mostrar resultados
            display_results(response)
    else:
        st.warning("⚠️ Por favor, escribe una pregunta o selecciona una sugerida.")

# --- HISTORIAL DE CHAT ---
if st.session_state.chat_history:
    st.header("📚 Historial de Consultas")
    
    # Mostrar las últimas 5 interacciones
    recent_history = st.session_state.chat_history[-10:]  # Últimas 5 preguntas y respuestas
    
    for i in range(0, len(recent_history), 2):
        if i + 1 < len(recent_history):
            question_item = recent_history[i]
            response_item = recent_history[i + 1]
            
            with st.expander(f"❓ {question_item['content'][:50]}..."):
                st.write(f"**Pregunta:** {question_item['content']}")
                
                if response_item['content'].get('interpretation'):
                    st.write(f"**Respuesta:** {response_item['content']['interpretation']}")
                
                if response_item['content'].get('results'):
                    st.write(f"**Registros encontrados:** {len(response_item['content']['results'])}")

# --- PANEL LATERAL CON INFORMACIÓN ---
st.sidebar.header("🔧 Panel de Control")

# Alerta de stock bajo
st.sidebar.subheader("⚠️ Alerta de Stock Bajo")
threshold = st.sidebar.slider("Umbral de stock bajo:", 1, 100, 50)

if st.sidebar.button("🔍 Verificar Stock Bajo"):
    with st.spinner("Consultando productos con stock bajo..."):
        low_stock = agent.get_low_stock_alert(threshold)
        if low_stock:
            st.sidebar.error(f"⚠️ {len(low_stock)} productos con stock ≤ {threshold}")
            for item in low_stock[:5]:  # Mostrar solo los primeros 5
                st.sidebar.write(f"• {item['nombre']}: {item['cantidad']} unidades")
        else:
            st.sidebar.success("✅ No hay productos con stock bajo")

# Sugerencias de productos
st.sidebar.subheader("💡 Productos disponibles")
try:
    suggestions = agent.get_product_suggestions()
    st.sidebar.write("Algunos productos en stock:")
    for suggestion in suggestions[:10]:
        st.sidebar.write(f"• {suggestion}")
except:
    st.sidebar.write("No se pudieron cargar las sugerencias")

# Información del agente
st.sidebar.subheader("🤖 Información del Agente")
st.sidebar.info("""
**Capacidades:**
- Consultas en lenguaje natural
- Generación automática de SQL
- Análisis inteligente de resultados
- Alertas de stock bajo
- Reportes personalizados

**Ejemplos de preguntas:**
- "¿Qué productos vencen esta semana?"
- "¿Cuál es el producto más vendido?"
- "¿Cuánto dinero tengo en inventario?"
- "¿Qué proveedores tengo registrados?"
""")

# Botón para limpiar historial
if st.sidebar.button("🗑️ Limpiar Historial"):
    st.session_state.chat_history = []
    st.rerun()