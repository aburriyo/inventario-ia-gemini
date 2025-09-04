# 🤖 Sistema de Gestión de Inventario con IA

Un sistema completo de gestión de inventario de alimentos con agente inteligente powered by Gemini 2.5 Pro para consultas en lenguaje natural.

## 🌟 Características

### 📊 Dashboard de Inventario
- Visualización completa del inventario
- Gráficos interactivos con Plotly
- Alertas de stock bajo configurables
- Historial de movimientos

### 🤖 Agente Inteligente
- Consultas en lenguaje natural usando Gemini 2.5 Pro
- Interpretación inteligente de resultados
- Consultas SQL automáticas
- Sistema de fallback robusto

### 💬 Chat Interactivo
- Interfaz conversacional intuitiva
- Preguntas sugeridas
- Historial de consultas
- Descarga de datos en CSV

## 🚀 Tecnologías Utilizadas

- **Backend**: Python, MySQL
- **Frontend**: Streamlit
- **IA**: Google Gemini 2.5 Pro
- **Visualización**: Plotly Express
- **Base de Datos**: MySQL

## 📋 Requisitos

```bash
streamlit
pandas
mysql-connector-python
plotly
google-generativeai
python-dotenv
toml
```

## ⚙️ Configuración

### 1. Base de Datos
Configura tu conexión MySQL en `.streamlit/secrets.toml`:

```toml
[connections.mysql]
host = "tu_host"
port = 3306
database = "inventario_alimentos"
user = "tu_usuario"
password = "tu_password"
```

### 2. Variables de Entorno
Crea un archivo `.env` con tu API key de Gemini:

```env
GEMINI_API_KEY="tu_api_key_de_gemini"
```

### 3. Instalación
```bash
pip install -r requirements.txt
```

## 🎯 Uso

### Dashboard Principal
```bash
streamlit run streamlit_db.py
```

### Agente de Chat IA
```bash
streamlit run chat_agent.py --server.port 8503
```

## 💬 Ejemplos de Consultas

El agente puede responder preguntas como:

- "¿Qué productos tengo en stock?"
- "¿Cuáles productos tienen stock bajo?"
- "¿Qué productos vencen esta semana?"
- "¿Cuántos productos tengo por proveedor?"
- "¿Cuál es el valor total de mi inventario?"
- "¿Qué productos son más caros?"

## 📁 Estructura del Proyecto

```
├── streamlit_db.py          # Dashboard principal
├── chat_agent.py            # Interfaz de chat IA
├── database_agent.py        # Agente inteligente
├── services.py              # Servicios auxiliares
├── app.py                   # Aplicación Flask (si aplica)
├── requirements.txt         # Dependencias
├── .streamlit/
│   └── secrets.toml        # Configuración de BD
├── static/                 # Archivos estáticos
├── templates/              # Templates HTML
└── README.md              # Este archivo
```

## 🔧 Funcionalidades del Agente

### Consultas Inteligentes
- **Generación SQL automática**: Convierte lenguaje natural a SQL
- **Interpretación contextual**: Analiza y explica resultados
- **Consultas predefinidas**: Para casos comunes y eficiencia
- **Modo fallback**: Funciona sin conexión a Gemini

### Análisis Automático
- Estadísticas de inventario
- Alertas de stock crítico
- Cálculo de valor total
- Recomendaciones inteligentes

## 🛠️ Desarrollo

### Agregar Nuevas Consultas
1. Edita `database_agent.py`
2. Agrega patrones de palabras clave en `_generate_sql_query`
3. Incluye interpretación específica en `_basic_interpretation`

### Extender Funcionalidades
- Agregar nuevos tipos de agentes
- Integrar más fuentes de datos
- Implementar notificaciones automáticas

## 📊 Schema de Base de Datos

```sql
-- Productos
CREATE TABLE productos (
    id INT PRIMARY KEY,
    nombre VARCHAR(255),
    cantidad INT,
    precio_venta DECIMAL(10,2),
    id_categoria INT,
    id_proveedor INT,
    fecha_caducidad DATE
);

-- Categorías
CREATE TABLE categorias (
    id INT PRIMARY KEY,
    nombre VARCHAR(255)
);

-- Proveedores
CREATE TABLE proveedores (
    id INT PRIMARY KEY,
    nombre VARCHAR(255),
    contacto VARCHAR(255)
);

-- Movimientos
CREATE TABLE movimientos_inventario (
    id INT PRIMARY KEY,
    id_producto INT,
    tipo_movimiento VARCHAR(50),
    cantidad INT,
    fecha DATETIME,
    descripcion TEXT
);
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🙏 Agradecimientos

- Google Gemini 2.5 Pro por las capacidades de IA
- Streamlit por la increíble interfaz web
- Plotly por las visualizaciones interactivas

---

⭐ ¡Si este proyecto te ayuda, no olvides darle una estrella!