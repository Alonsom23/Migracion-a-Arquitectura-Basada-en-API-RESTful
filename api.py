from flask import Flask, request, jsonify
from database import get_redis_client, close_db_connection
import json
import uuid
import os
from redis.exceptions import RedisError

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "api_super_secret_key_default")

BOOK_KEY_PREFIX = "libro:"

# --- Funciones de Lógica de Negocio (CRUD) de la API ---

def _get_all_books_from_db():
    """Obtiene todos los libros de KeyDB."""
    r = get_redis_client()
    if r is None:
        return [], "DB_ERROR"

    books = []
    try:
        for key in r.scan_iter(f"{BOOK_KEY_PREFIX}*"):
            book_json = r.get(key)
            if book_json:
                try:
                    books.append(json.loads(book_json))
                except json.JSONDecodeError:
                    print(f"Advertencia: No se pudo decodificar el JSON para la clave {key}.")
                    continue
        books.sort(key=lambda x: x.get('titulo', '').lower())
        return books, None
    except RedisError as e:
        print(f"Error al obtener libros de KeyDB: {e}")
        return [], "DB_ERROR"

def _get_book_by_id_from_db(book_id: str):
    """Obtiene un libro específico por su ID."""
    r = get_redis_client()
    if r is None:
        return None, "DB_ERROR"

    key = f"{BOOK_KEY_PREFIX}{book_id}"
    try:
        book_json = r.get(key)
        if book_json:
            return json.loads(book_json), None
        return None, "NOT_FOUND"
    except RedisError as e:
        print(f"Error al obtener libro por ID de KeyDB: {e}")
        return None, "DB_ERROR"
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON para el libro {book_id}: {e}")
        return None, "INVALID_DATA"

def _add_book_to_db(titulo: str, autor: str, genero: str = None, leido: bool = False):
    """Agrega un nuevo libro a KeyDB."""
    r = get_redis_client()
    if r is None:
        return None, "DB_ERROR"

    book_id = str(uuid.uuid4())
    key = f"{BOOK_KEY_PREFIX}{book_id}"

    book_data = {
        "id": book_id,
        "titulo": titulo,
        "autor": autor,
        "genero": genero,
        "leido": leido
    }

    try:
        r.set(key, json.dumps(book_data))
        return book_data, None
    except RedisError as e:
        print(f"Error al agregar libro a KeyDB: {e}")
        return None, "DB_ERROR"

def _update_book_in_db(book_id: str, updates: dict):
    """Actualiza un libro existente en KeyDB."""
    r = get_redis_client()
    if r is None:
        return None, "DB_ERROR"

    key = f"{BOOK_KEY_PREFIX}{book_id}"
    try:
        book_json = r.get(key)
        if not book_json:
            return None, "NOT_FOUND"

        book_data = json.loads(book_json)
        updated = False
        for field, value in updates.items():
            if field in book_data and book_data.get(field) != value:
                book_data[field] = value
                updated = True

        if updated:
            r.set(key, json.dumps(book_data))
            return book_data, None
        return book_data, "NO_CHANGE" # No se realizaron cambios
    except RedisError as e:
        print(f"Error al actualizar libro en KeyDB: {e}")
        return None, "DB_ERROR"
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON para actualizar libro {book_id}: {e}")
        return None, "INVALID_DATA"

def _delete_book_from_db(book_id: str):
    """Elimina un libro de KeyDB."""
    r = get_redis_client()
    if r is None:
        return False, None, "DB_ERROR"

    key = f"{BOOK_KEY_PREFIX}{book_id}"
    try:
        # Obtener datos del libro antes de eliminar para devolverlos en la respuesta
        book_data = json.loads(r.get(key)) if r.exists(key) else None

        result = r.delete(key)
        if result > 0:
            return True, book_data, None
        return False, None, "NOT_FOUND"
    except RedisError as e:
        print(f"Error al eliminar libro de KeyDB: {e}")
        return False, None, "DB_ERROR"
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON para eliminar libro {book_id}: {e}")
        return False, None, "INVALID_DATA"

# --- Endpoints de la API RESTful ---

@app.route('/books', methods=['GET'])
def get_books():
    books, error = _get_all_books_from_db()
    if error == "DB_ERROR":
        return jsonify({"error": "Error interno del servidor al conectar con la base de datos."}), 500
    return jsonify(books), 200

@app.route('/books/<string:book_id>', methods=['GET'])
def get_book(book_id):
    book, error = _get_book_by_id_from_db(book_id)
    if error == "DB_ERROR":
        return jsonify({"error": "Error interno del servidor al conectar con la base de datos."}), 500
    if error == "NOT_FOUND":
        return jsonify({"message": "Libro no encontrado."}), 404
    if error == "INVALID_DATA":
        return jsonify({"error": "Datos inválidos en la base de datos para este libro."}), 500
    return jsonify(book), 200

@app.route('/books', methods=['POST'])
def add_book():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requiere JSON para esta solicitud."}), 400

    titulo = data.get('titulo')
    autor = data.get('autor')
    genero = data.get('genero')
    leido = data.get('leido', False)

    if not titulo or not autor:
        return jsonify({"error": "El título y el autor son campos obligatorios."}), 400

    book, error = _add_book_to_db(titulo, autor, genero, leido)
    if error == "DB_ERROR":
        return jsonify({"error": "Error interno del servidor al agregar el libro."}), 500

    return jsonify(book), 201 # 201 Created

@app.route('/books/<string:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Se requiere JSON para esta solicitud."}), 400

    # Validar que al menos un campo sea para actualizar
    if not any(key in data for key in ['titulo', 'autor', 'genero', 'leido']):
        return jsonify({"error": "No se proporcionaron campos válidos para actualizar."}), 400

    book, error = _update_book_in_db(book_id, data)
    if error == "DB_ERROR":
        return jsonify({"error": "Error interno del servidor al actualizar el libro."}), 500
    if error == "NOT_FOUND":
        return jsonify({"message": "Libro no encontrado para actualizar."}), 404
    if error == "INVALID_DATA":
        return jsonify({"error": "Datos inválidos en la solicitud para este libro."}), 400
    if error == "NO_CHANGE":
        return jsonify({"message": "No se realizaron cambios en el libro."}), 200 # O 204 No Content

    return jsonify(book), 200

@app.route('/books/<string:book_id>', methods=['DELETE'])
def delete_book(book_id):
    success, book_data, error = _delete_book_from_db(book_id)
    if error == "DB_ERROR":
        return jsonify({"error": "Error interno del servidor al eliminar el libro."}), 500
    if error == "NOT_FOUND":
        return jsonify({"message": "Libro no encontrado para eliminar."}), 404

    if success:
        return jsonify({"message": "Libro eliminado exitosamente.", "deleted_book": book_data}), 200
    else:
        return jsonify({"error": "Ocurrió un error inesperado al eliminar el libro."}), 500

# Manejo de errores de conexión global al iniciar la API
@app.before_request
def check_db_connection():
    if get_redis_client() is None and request.endpoint != 'static':
        # Si hay un error de DB, devolver error 500 para todas las rutas de API
        pass # No podemos devolver un jsonify aquí directamente, se manejará en cada ruta CRUD

# Cierra la conexión de KeyDB cuando la aplicación Flask se apaga
@app.teardown_appcontext
def teardown_db(exception):
    close_db_connection()

if __name__ == '__main__':
    app.run(debug=True, port=5001) # API correrá en el puerto 5001