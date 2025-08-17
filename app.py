from flask import Flask, render_template, request, redirect, url_for, flash
import requests # NUEVO: Importa la biblioteca requests para llamadas HTTP a la API
import os
from flask_mail import Mail, Message
from celery_app import make_celery
from dotenv import load_dotenv

# Cargar variables de entorno para Flask-Mail y API_BASE_URL
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "client_super_secret_key_default")

# NUEVO: URL base de la API RESTful
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5001') # Por defecto a 5001

# Configuración e inicialización de Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
mail = Mail(app)

# Inicializa Celery con el contexto de la aplicación Flask
celery = make_celery(app)

# NUEVO: Tarea de Celery para enviar correos electrónicos (misma que en tar8)
@celery.task
def send_email_task(subject, recipient, body):
    """Tarea asíncrona para enviar un correo electrónico usando Flask-Mail."""
    try:
        msg = Message(subject, recipients=[recipient], body=body)
        with app.app_context():
            mail.send(msg)
        print(f"Correo enviado a {recipient} con asunto '{subject}'")
        return "Correo enviado exitosamente."
    except Exception as e:
        print(f"Error al enviar correo a {recipient}: {e}")
        raise # Re-lanza la excepción para que Celery la marque como fallida

# --- Funciones de Interacción con la API (Reemplazan las funciones DB directas) ---

def get_all_books_from_api():
    """Obtiene todos los libros de la API REST."""
    try:
        response = requests.get(f"{API_BASE_URL}/books")
        response.raise_for_status() # Lanza HTTPError para errores 4xx/5xx
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Error de conexión a la API. Asegúrate de que la API esté funcionando."
    except requests.exceptions.RequestException as e:
        return None, f"Error al obtener libros de la API: {e}"
    except ValueError: # JSONDecodeError en versiones anteriores
        return None, "Respuesta inválida de la API (no es JSON válido)."

def get_book_from_api(book_id: str):
    """Obtiene un libro específico de la API REST."""
    try:
        response = requests.get(f"{API_BASE_URL}/books/{book_id}")
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Error de conexión a la API. Asegúrate de que la API esté funcionando."
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None, "Libro no encontrado en la API."
        return None, f"Error al obtener libro de la API: {e}"
    except ValueError:
        return None, "Respuesta inválida de la API (no es JSON válido)."

def add_book_to_api(titulo: str, autor: str, genero: str = None, leido: bool = False):
    """Agrega un libro a través de la API REST."""
    book_data = {
        "titulo": titulo,
        "autor": autor,
        "genero": genero,
        "leido": leido
    }
    try:
        response = requests.post(f"{API_BASE_URL}/books", json=book_data)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Error de conexión a la API. Asegúrate de que la API esté funcionando."
    except requests.exceptions.HTTPError as e:
        error_message = e.response.json().get('error', 'Error desconocido al agregar libro.') if e.response else 'Error desconocido.'
        return None, f"Error de API al agregar libro: {error_message} (Código: {e.response.status_code})"
    except ValueError:
        return None, "Respuesta inválida de la API (no es JSON válido)."

def update_book_in_api(book_id: str, updates: dict):
    """Actualiza un libro a través de la API REST."""
    try:
        response = requests.put(f"{API_BASE_URL}/books/{book_id}", json=updates)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Error de conexión a la API. Asegúrate de que la API esté funcionando."
    except requests.exceptions.HTTPError as e:
        error_message = e.response.json().get('error', 'Error desconocido al actualizar libro.') if e.response else 'Error desconocido.'
        if e.response.status_code == 404:
            return None, "Libro no encontrado para actualizar."
        return None, f"Error de API al actualizar libro: {error_message} (Código: {e.response.status_code})"
    except ValueError:
        return None, "Respuesta inválida de la API (no es JSON válido)."

def delete_book_from_api(book_id: str):
    """Elimina un libro a través de la API REST."""
    try:
        response = requests.delete(f"{API_BASE_URL}/books/{book_id}")
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Error de conexión a la API. Asegúrate de que la API esté funcionando."
    except requests.exceptions.HTTPError as e:
        error_message = e.response.json().get('message', 'Error desconocido al eliminar libro.') if e.response else 'Error desconocido.'
        if e.response.status_code == 404:
            return None, "Libro no encontrado para eliminar."
        return None, f"Error de API al eliminar libro: {error_message} (Código: {e.response.status_code})"
    except ValueError:
        return None, "Respuesta inválida de la API (no es JSON válido)."

# --- Rutas de la Aplicación Flask (Cliente) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """Ruta principal para listar y buscar libros."""
    search_query = request.args.get('search', '').strip()

    books, error = get_all_books_from_api()
    if error:
        flash(error, "danger")
        books = [] # Mostrar una lista vacía en caso de error

    if search_query and books:
        filtered_books = []
        query_lower = search_query.lower()
        for book in books:
            if (query_lower in book.get('titulo', '').lower() or
                query_lower in book.get('autor', '').lower() or
                (book.get('genero') and query_lower in book['genero'].lower())):
                filtered_books.append(book)
        books = filtered_books
        if not books:
            flash(f"No se encontraron libros que coincidan con '{search_query}'.", "info")

    if books: # Asegura que books sea una lista, incluso si está vacía
        books.sort(key=lambda x: x.get('titulo', '').lower())


    return render_template('index.html', books=books, search_query=search_query)

@app.route('/add', methods=['GET', 'POST'])
def add_book_route():
    """Ruta para agregar un nuevo libro."""
    if request.method == 'POST':
        titulo = request.form['titulo'].strip()
        autor = request.form['autor'].strip()
        genero = request.form.get('genero', '').strip()
        leido = request.form.get('leido') == 'on'

        if not titulo or not autor:
            flash('El título y el autor son obligatorios.', 'danger')
        else:
            book, error = add_book_to_api(titulo, autor, genero if genero else None, leido)
            if error:
                flash(f'Error al agregar libro: {error}', 'danger')
            else:
                flash(f'Libro "{titulo}" agregado exitosamente!', 'success')
                # Disparar tarea de Celery para enviar correo
                subject = f"Confirmación: Libro '{book.get('titulo', 'Desconocido')}' agregado a tu biblioteca"
                recipient = os.getenv('MAIL_DEFAULT_SENDER')
                body = f"Hola,\n\nSe ha agregado el libro '{book.get('titulo', 'Desconocido')}' de '{book.get('autor', 'Desconocido')}' a tu biblioteca personal.\n\n¡Disfruta la lectura!"
                send_email_task.delay(subject, recipient, body)
                return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/edit/<book_id>', methods=['GET', 'POST'])
def edit_book_route(book_id):
    """Ruta para editar un libro existente."""
    book, error = get_book_from_api(book_id)
    if error:
        flash(f'Error al cargar libro para edición: {error}', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        updates = {}
        new_titulo = request.form['titulo'].strip()
        new_autor = request.form['autor'].strip()
        new_genero = request.form.get('genero', '').strip()
        new_leido = request.form.get('leido') == 'on'

        if not new_titulo or not new_autor:
            flash('El título y el autor son obligatorios.', 'danger')
            return render_template('edit_book.html', book=book)

        # Preparar actualizaciones solo si han cambiado
        if new_titulo != book.get('titulo'): updates['titulo'] = new_titulo
        if new_autor != book.get('autor'): updates['autor'] = new_autor
        # Manejar género: si está vacío y antes no lo estaba, o viceversa
        if new_genero != book.get('genero', ''): updates['genero'] = new_genero if new_genero else None
        if new_leido != book.get('leido'): updates['leido'] = new_leido

        if not updates: # Si no hay cambios en los datos enviados
            flash('No se realizaron cambios en el libro.', 'info')
            return redirect(url_for('index'))

        updated_book, error = update_book_in_api(book_id, updates)
        if error:
            flash(f'Error al actualizar libro: {error}', 'danger')
        else:
            flash(f'Libro "{updated_book.get("titulo", "Desconocido")}" actualizado exitosamente!', 'success')
            return redirect(url_for('index'))

    return render_template('edit_book.html', book=book)

@app.route('/delete/<book_id>', methods=['GET'])
def confirm_delete_route(book_id):
    """Ruta para confirmar la eliminación de un libro."""
    book, error = get_book_from_api(book_id)
    if error:
        flash(f'Error al cargar libro para eliminación: {error}', 'danger')
        return redirect(url_for('index'))
    return render_template('confirm_delete.html', book=book)

@app.route('/delete/<book_id>/confirm', methods=['POST'])
def delete_book_confirmed_route(book_id):
    """Ruta para ejecutar la eliminación del libro después de la confirmación."""
    # Primero, intentar obtener el libro para el mensaje flash antes de eliminarlo
    book_to_delete, get_error = get_book_from_api(book_id)

    response_data, delete_error = delete_book_from_api(book_id)

    if delete_error:
        flash(f'Error al eliminar libro: {delete_error}', 'danger')
    else:
        # Usar los datos obtenidos antes de la eliminación si fue exitosa
        deleted_book_title = book_to_delete.get("titulo", "Desconocido") if book_to_delete else "Desconocido"
        deleted_book_author = book_to_delete.get("autor", "Desconocido") if book_to_delete else "Desconocido"

        flash(f'Libro "{deleted_book_title}" eliminado exitosamente!', 'success')

        # Disparar tarea de Celery para enviar correo
        subject = f"Confirmación: Libro '{deleted_book_title}' eliminado"
        recipient = os.getenv('MAIL_DEFAULT_SENDER')
        body = f"Hola,\n\nEl libro '{deleted_book_title}' de '{deleted_book_author}' ha sido eliminado de tu biblioteca personal.\n\nSaludos."
        send_email_task.delay(subject, recipient, body)

    return redirect(url_for('index'))

# Manejo de errores de conexión global a la API
@app.before_request
def check_api_availability():
    if not API_BASE_URL:
        flash("Error crítico: La URL de la API no está configurada en el entorno.", "danger")
        # Podrías redirigir a una página de error o simplemente dejar que la vista lo maneje
        return

if __name__ == '__main__':
    app.run(debug=True, port=5000) # Cliente Flask correrá en el puerto 5000