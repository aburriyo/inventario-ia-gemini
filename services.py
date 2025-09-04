import os
import google.generativeai as genai
import sqlite3
import json
import re

# Configurar la API de Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configuración del modelo
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  # ... (puedes añadir más configuraciones de seguridad)
]

model = genai.GenerativeModel(model_name="gemini-2.5-flash",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

def execute_database_query(query):
    """
    Ejecuta una consulta SQL en la base de datos y devuelve los resultados.
    """
    try:
        # Obtener la ruta absoluta del directorio del proyecto
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'app.db')
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
        cursor = conn.cursor()
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        results_list = [dict(row) for row in results]
        
        conn.close()
        return results_list
        
    except Exception as e:
        print(f"Error al ejecutar consulta: {e}")
        return None

def analyze_user_intent(message):
    """
    Analiza el mensaje del usuario para determinar si necesita consultar la base de datos
    y generar la consulta SQL apropiada.
    """
    message_lower = message.lower()
    
    # Patrones comunes para consultas de productos
    stock_patterns = ['stock', 'inventario', 'cantidad', 'cuántos', 'cuantos']
    price_patterns = ['precio', 'costo', 'vale', 'cuesta']
    product_patterns = ['producto', 'artículo', 'item']
    
    # Verificar si es una consulta de stock
    if any(pattern in message_lower for pattern in stock_patterns):
        # Extraer el nombre del producto
        product_match = re.search(r'producto\s+([a-zA-Z0-9\s]+)', message_lower)
        if product_match:
            product_name = product_match.group(1).strip()
            query = f"SELECT name, stock FROM product WHERE LOWER(name) LIKE '%{product_name}%'"
            return 'stock', query
        else:
            # Buscar todos los stocks
            query = "SELECT name, stock FROM product ORDER BY name"
            return 'stock_all', query
    
    # Verificar si es una consulta de precio
    elif any(pattern in message_lower for pattern in price_patterns):
        product_match = re.search(r'producto\s+([a-zA-Z0-9\s]+)', message_lower)
        if product_match:
            product_name = product_match.group(1).strip()
            query = f"SELECT name, price FROM product WHERE LOWER(name) LIKE '%{product_name}%'"
            return 'price', query
        else:
            query = "SELECT name, price FROM product ORDER BY name"
            return 'price_all', query
    
    # Verificar si es una consulta general de productos
    elif any(pattern in message_lower for pattern in product_patterns):
        query = "SELECT * FROM product ORDER BY name"
        return 'products', query
    
    return None, None

def format_database_response(query_type, results):
    """
    Formatea los resultados de la base de datos en una respuesta legible.
    """
    if not results:
        return "No se encontraron resultados en la base de datos."
    
    if query_type == 'stock':
        if len(results) == 1:
            product = results[0]
            if product['stock'] > 0:
                return f"El {product['name']} tiene {product['stock']} unidades en stock."
            else:
                return f"El {product['name']} está agotado (0 unidades en stock)."
        else:
            response = "Stock de productos encontrados:\n"
            for product in results:
                status = f"{product['stock']} unidades" if product['stock'] > 0 else "AGOTADO"
                response += f"• {product['name']}: {status}\n"
            return response
    
    elif query_type == 'stock_all':
        response = "Stock de todos los productos:\n"
        for product in results:
            status = f"{product['stock']} unidades" if product['stock'] > 0 else "AGOTADO"
            response += f"• {product['name']}: {status}\n"
        return response
    
    elif query_type == 'price':
        if len(results) == 1:
            product = results[0]
            return f"El precio del {product['name']} es ${product['price']:.2f}"
        else:
            response = "Precios de productos encontrados:\n"
            for product in results:
                response += f"• {product['name']}: ${product['price']:.2f}\n"
            return response
    
    elif query_type == 'price_all':
        response = "Precios de todos los productos:\n"
        for product in results:
            response += f"• {product['name']}: ${product['price']:.2f}\n"
        return response
    
    elif query_type == 'products':
        response = "Información de productos:\n"
        for product in results:
            stock_info = f"{product['stock']} unidades" if product['stock'] > 0 else "AGOTADO"
            response += f"• {product['name']}: ${product['price']:.2f} - Stock: {stock_info}\n"
        return response
    
    return "Información encontrada en la base de datos."

def get_ai_response(message):
    """
    Toma un mensaje de texto y devuelve una respuesta generada por Gemini,
    incluyendo consultas a la base de datos cuando sea necesario.
    """
    print(f"Mensaje recibido para Gemini: {message}")
    
    try:
        # Primero, verificar si necesita consultar la base de datos
        query_type, sql_query = analyze_user_intent(message)
        
        if query_type and sql_query:
            print(f"Ejecutando consulta SQL: {sql_query}")
            db_results = execute_database_query(sql_query)
            
            if db_results:
                # Formatear respuesta con datos de la base de datos
                db_response = format_database_response(query_type, db_results)
                print(f"Respuesta de la base de datos: {db_response}")
                return db_response
            else:
                return "No se encontró información sobre ese producto en nuestra base de datos."
        
        # Si no necesita consultar la base de datos, usar Gemini normalmente
        convo = model.start_chat(history=[])
        
        # Mejorar el prompt para darle más contexto al modelo
        prompt = f"""Eres un asistente de ventas útil y amigable. 
        Responde de forma concisa y profesional. 
        Si el usuario pregunta por productos específicos, stock, precios o inventario, 
        menciona que pueden hacer consultas específicas sobre productos disponibles.
        
        El usuario dice: '{message}'"""
        
        convo.send_message(prompt)
        reply = convo.last.text
        
        print(f"Respuesta de Gemini: {reply}")
        return reply
        
    except Exception as e:
        print(f"Error al procesar la solicitud: {e}")
        return "Hubo un error al procesar tu solicitud. Por favor, inténtalo de nuevo."