import google.generativeai as genai
import mysql.connector
import toml
import os
from dotenv import load_dotenv
import json
import re

class DatabaseAgent:
    def __init__(self):
        # Cargar variables de entorno
        load_dotenv()
        
        # Configurar Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Configurar conexión a base de datos
        self.db_config = self._load_db_config()
        
        # Schema de la base de datos para el contexto del agente
        self.db_schema = """
        ESQUEMA DE BASE DE DATOS:
        
        Tabla: productos
        - id (INT, PRIMARY KEY)
        - nombre (VARCHAR)
        - cantidad (INT)
        - precio_venta (DECIMAL)
        - id_categoria (INT, FK)
        - id_proveedor (INT, FK)
        - fecha_caducidad (DATE)
        
        Tabla: categorias
        - id (INT, PRIMARY KEY)
        - nombre (VARCHAR)
        
        Tabla: proveedores
        - id (INT, PRIMARY KEY)
        - nombre (VARCHAR)
        - contacto (VARCHAR)
        
        Tabla: movimientos_inventario
        - id (INT, PRIMARY KEY)
        - id_producto (INT, FK)
        - tipo_movimiento (VARCHAR: 'entrada' o 'salida')
        - cantidad (INT)
        - fecha (DATETIME)
        - descripcion (TEXT)
        """
    
    def _load_db_config(self):
        """Cargar configuración de base de datos"""
        try:
            secrets_path = '.streamlit/secrets.toml'
            with open(secrets_path, 'r') as f:
                secrets = toml.load(f)
            return secrets['connections']['mysql']
        except Exception as e:
            raise Exception(f"Error cargando configuración de BD: {e}")
    
    def _connect_db(self):
        """Crear conexión a la base de datos"""
        return mysql.connector.connect(**self.db_config)
    
    def _execute_query(self, query, params=None):
        """Ejecutar consulta en la base de datos"""
        try:
            conn = self._connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            return f"Error ejecutando consulta: {e}"
    
    def _generate_sql_query(self, user_question):
        """Generar consulta SQL usando Gemini o consultas predefinidas"""
        
        # Diccionario de consultas predefinidas para casos comunes
        predefined_queries = {
            "stock": """
                SELECT p.id, p.nombre, p.cantidad, p.precio_venta, 
                       c.nombre as categoria, pr.nombre as proveedor, 
                       p.fecha_caducidad
                FROM productos p 
                LEFT JOIN categorias c ON p.id_categoria = c.id 
                LEFT JOIN proveedores pr ON p.id_proveedor = pr.id 
                WHERE p.cantidad > 0
                ORDER BY p.nombre 
                LIMIT 50
            """,
            "stock_bajo": """
                SELECT p.id, p.nombre, p.cantidad, p.precio_venta, 
                       c.nombre as categoria, pr.nombre as proveedor
                FROM productos p 
                LEFT JOIN categorias c ON p.id_categoria = c.id 
                LEFT JOIN proveedores pr ON p.id_proveedor = pr.id 
                WHERE p.cantidad <= 50
                ORDER BY p.cantidad ASC 
                LIMIT 50
            """,
            "vencimiento": """
                SELECT p.id, p.nombre, p.cantidad, p.fecha_caducidad, 
                       c.nombre as categoria, pr.nombre as proveedor,
                       DATEDIFF(p.fecha_caducidad, CURDATE()) as dias_para_vencer
                FROM productos p 
                LEFT JOIN categorias c ON p.id_categoria = c.id 
                LEFT JOIN proveedores pr ON p.id_proveedor = pr.id 
                WHERE p.fecha_caducidad <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
                ORDER BY p.fecha_caducidad ASC 
                LIMIT 50
            """,
            "proveedores": """
                SELECT pr.nombre as proveedor, 
                       COUNT(p.id) as total_productos,
                       SUM(p.cantidad) as total_unidades
                FROM proveedores pr 
                LEFT JOIN productos p ON pr.id = p.id_proveedor 
                GROUP BY pr.id, pr.nombre
                ORDER BY total_productos DESC
            """,
            "categorias": """
                SELECT c.nombre as categoria, 
                       COUNT(p.id) as total_productos,
                       SUM(p.cantidad) as total_unidades
                FROM categorias c 
                LEFT JOIN productos p ON c.id = p.id_categoria 
                GROUP BY c.id, c.nombre
                ORDER BY total_productos DESC
            """,
            "mas_caros": """
                SELECT p.nombre, p.precio_venta, p.cantidad, 
                       c.nombre as categoria, pr.nombre as proveedor
                FROM productos p 
                LEFT JOIN categorias c ON p.id_categoria = c.id 
                LEFT JOIN proveedores pr ON p.id_proveedor = pr.id 
                ORDER BY p.precio_venta DESC 
                LIMIT 10
            """
        }
        
        # Determinar qué consulta usar basado en palabras clave
        question_lower = user_question.lower()
        
        if any(word in question_lower for word in ["stock bajo", "poco stock", "stock menor", "bajo stock"]):
            return predefined_queries["stock_bajo"]
        elif any(word in question_lower for word in ["vencen", "caducan", "expiran", "vencimiento"]):
            return predefined_queries["vencimiento"]
        elif any(word in question_lower for word in ["proveedor", "proveedores"]):
            return predefined_queries["proveedores"]
        elif any(word in question_lower for word in ["categoria", "categorías", "categorias"]):
            return predefined_queries["categorias"]
        elif any(word in question_lower for word in ["caros", "caro", "precio alto", "más caros"]):
            return predefined_queries["mas_caros"]
        elif any(word in question_lower for word in ["stock", "productos", "inventario", "tengo"]):
            return predefined_queries["stock"]
        
        # Si no hay coincidencia, intentar con Gemini
        try:
            prompt = f"""
            Eres un experto en SQL que ayuda a consultar una base de datos de inventario de alimentos.
            
            {self.db_schema}
            
            PREGUNTA DEL USUARIO: {user_question}
            
            INSTRUCCIONES:
            1. Genera una consulta SQL válida para responder la pregunta
            2. Usa JOINS cuando sea necesario para obtener información completa
            3. Incluye nombres de categorías y proveedores en lugar de solo IDs
            4. Limita resultados a 50 filas máximo usando LIMIT
            5. Usa ORDER BY para organizar resultados de manera lógica
            
            RESPONDE SOLO CON LA CONSULTA SQL, SIN EXPLICACIONES ADICIONALES.
            """
            
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Limpiar la respuesta para obtener solo el SQL
            sql_query = re.sub(r'```sql|```', '', sql_query).strip()
            
            return sql_query
            
        except Exception as e:
            # Fallback a consulta general de productos
            print(f"Warning: Error con Gemini API, usando consulta predefinida: {e}")
            return predefined_queries["stock"]
    
    def _interpret_results(self, query_results, user_question):
        """Interpretar resultados usando Gemini o interpretación básica"""
        # Si no hay resultados, dar una respuesta apropiada
        if not query_results or len(query_results) == 0:
            return f"No se encontraron resultados para tu consulta: '{user_question}'. Verifica que los productos existan en la base de datos o intenta reformular tu pregunta."
        
        # Intentar con Gemini primero
        try:
            prompt = f"""
            Eres un asistente especializado en inventario de alimentos que interpreta resultados de base de datos.
            
            PREGUNTA ORIGINAL: {user_question}
            
            RESULTADOS DE LA BASE DE DATOS:
            {json.dumps(query_results, indent=2, default=str)}
            
            INSTRUCCIONES:
            1. Proporciona una respuesta natural y útil en español
            2. Resalta información importante como stock bajo, productos próximos a vencer, etc.
            3. Si no hay resultados, sugiere alternativas o productos similares
            4. Incluye recomendaciones cuando sea apropiado
            5. Usa formato claro con bullet points cuando sea necesario
            6. Sé específico con números y datos encontrados
            
            RESPUESTA:
            """
            
            response = self.model.generate_content(prompt)
            if response.text:
                return response.text
            else:
                # Fallback a interpretación básica
                return self._basic_interpretation(query_results, user_question)
                
        except Exception as e:
            print(f"Warning: Error con Gemini para interpretación, usando interpretación básica: {e}")
            # Fallback a interpretación básica
            return self._basic_interpretation(query_results, user_question)
    
    def _basic_interpretation(self, query_results, user_question):
        """Interpretación básica sin IA"""
        count = len(query_results)
        question_lower = user_question.lower()
        
        # Interpretaciones específicas según el tipo de consulta
        if any(word in question_lower for word in ["stock bajo", "poco stock", "stock menor"]):
            if count == 0:
                return "🟢 **¡Buenas noticias!** No hay productos con stock bajo en este momento."
            else:
                productos_criticos = [p for p in query_results if p.get('cantidad', 0) <= 20]
                msg = f"⚠️ **Se encontraron {count} productos con stock bajo:**\n\n"
                for i, producto in enumerate(query_results[:10], 1):
                    cantidad = producto.get('cantidad', 0)
                    emoji = "🔴" if cantidad <= 20 else "🟡"
                    msg += f"{emoji} **{producto.get('nombre', 'N/A')}**: {cantidad} unidades\n"
                if len(productos_criticos) > 0:
                    msg += f"\n💡 **Recomendación**: {len(productos_criticos)} productos necesitan reposición urgente (≤20 unidades)."
                return msg
                
        elif any(word in question_lower for word in ["vencen", "caducan", "expiran"]):
            if count == 0:
                return "🟢 **¡Perfecto!** No hay productos próximos a vencer en los próximos 30 días."
            else:
                msg = f"⚠️ **Se encontraron {count} productos que vencen pronto:**\n\n"
                for i, producto in enumerate(query_results[:10], 1):
                    fecha = producto.get('fecha_caducidad', 'N/A')
                    dias = producto.get('dias_para_vencer', 'N/A')
                    emoji = "🔴" if isinstance(dias, int) and dias <= 7 else "🟡"
                    msg += f"{emoji} **{producto.get('nombre', 'N/A')}**: Vence {fecha}\n"
                return msg
                
        elif any(word in question_lower for word in ["proveedor", "proveedores"]):
            msg = f"📊 **Distribución por proveedores ({count} proveedores):**\n\n"
            for i, proveedor in enumerate(query_results[:10], 1):
                nombre = proveedor.get('proveedor', 'N/A')
                productos = proveedor.get('total_productos', 0)
                unidades = proveedor.get('total_unidades', 0)
                msg += f"🏦 **{nombre}**: {productos} productos, {unidades} unidades totales\n"
            return msg
            
        elif any(word in question_lower for word in ["categoria", "categorías"]):
            msg = f"📦 **Distribución por categorías ({count} categorías):**\n\n"
            for i, categoria in enumerate(query_results[:10], 1):
                nombre = categoria.get('categoria', 'N/A')
                productos = categoria.get('total_productos', 0)
                unidades = categoria.get('total_unidades', 0)
                msg += f"🏷️ **{nombre}**: {productos} productos, {unidades} unidades totales\n"
            return msg
            
        elif any(word in question_lower for word in ["caros", "caro", "precio alto"]):
            msg = f"💰 **Los {count} productos más caros del inventario:**\n\n"
            for i, producto in enumerate(query_results[:10], 1):
                nombre = producto.get('nombre', 'N/A')
                precio = producto.get('precio_venta', 0)
                cantidad = producto.get('cantidad', 0)
                categoria = producto.get('categoria', 'N/A')
                msg += f"{i}. **{nombre}**: ${precio} ({cantidad} unidades) - {categoria}\n"
            return msg
            
        else:
            # Interpretación general para productos en stock
            msg = f"📦 **Se encontraron {count} productos en tu inventario:**\n\n"
            
            # Estadísticas básicas
            total_unidades = sum(p.get('cantidad', 0) for p in query_results)
            valor_total = sum(float(p.get('precio_venta', 0)) * p.get('cantidad', 0) for p in query_results)
            
            msg += f"📊 **Resumen:**\n"
            msg += f"• Total productos: {count}\n"
            msg += f"• Total unidades: {total_unidades:,}\n"
            msg += f"• Valor estimado inventario: ${valor_total:,.2f}\n\n"
            
            # Productos con menos stock (para alertas)
            productos_bajo_stock = [p for p in query_results if p.get('cantidad', 0) <= 50]
            if productos_bajo_stock:
                msg += f"⚠️ **Alerta**: {len(productos_bajo_stock)} productos con stock ≤ 50 unidades\n\n"
            
            # Mostrar algunos productos de ejemplo
            msg += "📋 **Algunos productos destacados:**\n"
            for i, producto in enumerate(query_results[:5], 1):
                nombre = producto.get('nombre', 'N/A')
                cantidad = producto.get('cantidad', 0)
                precio = producto.get('precio_venta', 0)
                categoria = producto.get('categoria', 'N/A')
                msg += f"• **{nombre}**: {cantidad} unidades (${precio}) - {categoria}\n"
                
            if count > 5:
                msg += f"\n... y {count - 5} productos más."
            
            return msg
    
    def ask(self, question):
        """Función principal para hacer preguntas al agente"""
        try:
            # Paso 1: Generar consulta SQL
            sql_query = self._generate_sql_query(question)
            
            if sql_query.startswith("Error"):
                return {"error": sql_query, "sql": None, "results": None, "interpretation": None}
            
            # Paso 2: Ejecutar consulta
            results = self._execute_query(sql_query)
            
            if isinstance(results, str):  # Error en la consulta
                return {"error": results, "sql": sql_query, "results": None, "interpretation": None}
            
            # Paso 3: Interpretar resultados
            interpretation = self._interpret_results(results, question)
            
            return {
                "sql": sql_query,
                "results": results,
                "interpretation": interpretation,
                "count": len(results) if results else 0
            }
            
        except Exception as e:
            return {"error": f"Error general: {e}", "sql": None, "results": None, "interpretation": None}
    
    def get_product_suggestions(self):
        """Obtener sugerencias de productos disponibles"""
        query = """
        SELECT DISTINCT nombre 
        FROM productos 
        WHERE cantidad > 0 
        ORDER BY nombre 
        LIMIT 20
        """
        results = self._execute_query(query)
        return [item['nombre'] for item in results] if results else []
    
    def get_low_stock_alert(self, threshold=50):
        """Obtener alerta de stock bajo"""
        query = f"""
        SELECT p.nombre, p.cantidad, c.nombre as categoria 
        FROM productos p 
        LEFT JOIN categorias c ON p.id_categoria = c.id 
        WHERE p.cantidad <= %s 
        ORDER BY p.cantidad ASC
        """
        return self._execute_query(query, (threshold,))

# Función para testing
if __name__ == "__main__":
    agent = DatabaseAgent()
    
    # Test simple primero
    print("=== TESTING DATABASE AGENT ===")
    
    # Test conexión a BD
    try:
        conn = agent._connect_db()
        print("✅ Conexión a BD exitosa")
        conn.close()
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        exit()
    
    # Test consulta simple
    print("\n=== TEST CONSULTA SIMPLE ===")
    simple_query = "SELECT COUNT(*) as total FROM productos"
    result = agent._execute_query(simple_query)
    print(f"Total productos en BD: {result}")
    
    # Test generación de SQL
    print("\n=== TEST GENERACIÓN SQL ===")
    question = "¿Qué productos tengo en stock?"
    sql = agent._generate_sql_query(question)
    print(f"SQL Generado: {sql}")
    
    # Test consulta completa
    print("\n=== TEST CONSULTA COMPLETA ===")
    response = agent.ask(question)
    print(f"Respuesta completa: {json.dumps(response, indent=2, default=str)}")
    
    print("\n=== EJEMPLOS DE USO ===")
    # Ejemplos de uso
    test_questions = [
        "¿Qué productos tengo en stock?",
        "¿Cuáles son los productos con stock bajo?",
    ]
    
    for question in test_questions:
        print(f"\nPREGUNTA: {question}")
        response = agent.ask(question)
        print(f"SQL: {response.get('sql', 'N/A')}")
        print(f"Resultados: {len(response.get('results', []))} registros")
        print(f"RESPUESTA: {response.get('interpretation', 'N/A')}")
        print("-" * 50)