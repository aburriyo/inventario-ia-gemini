import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Inventario",
    page_icon="📦",
    layout="wide",
)

# --- CONEXIÓN A LA BASE DE DATOS ---
# Inicializa la conexión.
# Streamlit usa st.connection para manejar las conexiones de forma segura y eficiente.
@st.cache_resource
def init_connection():
    try:
        return mysql.connector.connect(**st.secrets["connections"]["mysql"])
    except KeyError:
        # Fallback: leer directamente del archivo si st.secrets falla
        import toml
        import os
        secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
        with open(secrets_path, 'r') as f:
            secrets = toml.load(f)
        return mysql.connector.connect(**secrets["connections"]["mysql"])

conn = init_connection()

# --- FUNCIONES PARA CONSULTAS ---
# Usa st.cache_data para que las consultas no se ejecuten en cada re-renderizado.
@st.cache_data(ttl=600) # Cache por 10 minutos
def run_query(query):
    with conn.cursor(dictionary=True) as cur:
        cur.execute(query)
        return cur.fetchall()

# --- APLICACIÓN PRINCIPAL ---

st.title("📦 Dashboard de Inventario de Alimentos")

# --- OBTENER Y MOSTRAR DATOS ---
st.header("Inventario Completo de Productos")

# Query para obtener una vista completa de los productos con sus categorías y proveedores
query_productos = """
SELECT
    p.id,
    p.nombre,
    p.cantidad,
    p.precio_venta,
    c.nombre AS categoria,
    pr.nombre AS proveedor,
    p.fecha_caducidad
FROM productos p
LEFT JOIN categorias c ON p.id_categoria = c.id
LEFT JOIN proveedores pr ON p.id_proveedor = pr.id
ORDER BY p.nombre;
"""

# Ejecutar la consulta y cargar en un DataFrame de Pandas
try:
    results = run_query(query_productos)
    df_productos = pd.DataFrame(results)

    # Mostrar la tabla de datos interactiva
    st.dataframe(df_productos, use_container_width=True)

    st.success(f"Se encontraron {len(df_productos)} productos en el inventario.")

    # --- VISUALIZACIONES ---
    st.header("📊 Visualizaciones del Inventario")

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico 1: Cantidad de productos por categoría
        st.subheader("Productos por Categoría")
        df_cat_count = df_productos['categoria'].value_counts().reset_index()
        df_cat_count.columns = ['Categoría', 'Número de Productos']
        fig_cat = px.pie(df_cat_count, names='Categoría', values='Número de Productos',
                         title='Distribución de Productos por Categoría')
        st.plotly_chart(fig_cat, use_container_width=True)

    with col2:
        # Gráfico 2: Stock total por proveedor
        st.subheader("Stock Total por Proveedor")
        df_prov_stock = df_productos.groupby('proveedor')['cantidad'].sum().reset_index()
        df_prov_stock.columns = ['Proveedor', 'Stock Total']
        fig_prov = px.bar(df_prov_stock.sort_values('Stock Total', ascending=False),
                          x='Proveedor', y='Stock Total', title='Cantidad de Unidades por Proveedor')
        st.plotly_chart(fig_prov, use_container_width=True)


    # --- ALERTA DE BAJO STOCK ---
    st.header("⚠️ Alerta de Bajo Stock")

    # Slider para que el usuario defina qué es "bajo stock"
    umbral_stock_bajo = st.slider('Selecciona el umbral para "bajo stock":', 0, 150, 50)

    # Filtrar productos por debajo del umbral
    df_bajo_stock = df_productos[df_productos['cantidad'] <= umbral_stock_bajo]

    if not df_bajo_stock.empty:
        st.warning(f"Se encontraron {len(df_bajo_stock)} productos con stock igual or inferior a {umbral_stock_bajo} unidades.")
        st.dataframe(df_bajo_stock, use_container_width=True)
    else:
        st.success("¡Buenas noticias! No hay productos con bajo stock según el umbral seleccionado.")


    # Opción para ver los datos de movimientos
    if st.checkbox("Mostrar historial de movimientos de inventario"):
        st.header("Historial de Movimientos")
        query_movimientos = """
        SELECT
            m.id,
            p.nombre AS producto,
            m.tipo_movimiento,
            m.cantidad,
            m.fecha,
            m.descripcion
        FROM movimientos_inventario m
        JOIN productos p ON m.id_producto = p.id
        ORDER BY m.fecha DESC;
        """
        results_mov = run_query(query_movimientos)
        df_movimientos = pd.DataFrame(results_mov)
        st.dataframe(df_movimientos, use_container_width=True)

except Exception as e:
    st.error(f"Error al conectar o consultar la base de datos: {e}")
    st.info("Verifica que tu dirección IP esté autorizada en el firewall del Droplet y que las credenciales en 'secrets.toml' sean correctas.")