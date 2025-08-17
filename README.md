📚 Biblioteca Personal – Arquitectura con API REST y Cliente Flask
🎯 Objetivo

Separar la arquitectura de la aplicación web en dos componentes:

API RESTful (backend de datos): Proveedor de datos que expone endpoints CRUD en JSON.

Aplicación Flask (cliente): Consume la API REST mediante solicitudes HTTP y renderiza las vistas.

Esta separación permite construir una aplicación escalable, desacoplada y lista para producción.

📝 Contexto

En versiones anteriores, la aplicación Flask accedía directamente a la base de datos (KeyDB, MongoDB, etc.).
En esta versión:

La API REST gestiona los datos y expone endpoints HTTP.

La app Flask cliente interactúa únicamente con la API, sin acceder directamente a la base de datos.

📌 Requisitos Funcionales
🔹 API RESTful (Backend de Datos)

Endpoints principales:

GET /books → Lista de todos los libros

GET /books/<id> → Información de un libro específico

POST /books → Agregar un nuevo libro

PUT /books/<id> → Actualizar un libro

DELETE /books/<id> → Eliminar un libro

✔️ Respuestas en JSON
✔️ Códigos de estado HTTP correctos (200, 201, 400, 404, etc.)

🔹 Aplicación Flask (Cliente)

El cliente Flask debe:

Usar requests para comunicarse con la API.

Renderizar las vistas dinámicamente con los datos de la API.

Manejar errores de red y respuestas inválidas.

Mostrar mensajes de éxito/error al usuario en operaciones CRUD.

🚀 Entorno de Producción

Cliente Flask se despliega con Gunicorn + Nginx.

La API REST puede estar en el mismo servidor o en uno distinto.

Configuración de rutas mediante variables de entorno (.env).

💡 Consideraciones Técnicas

API implementada con Flask o Flask-RESTful.

Proyecto de la API separado, modular y con rutas limpias.

Cliente Flask usa requests para interactuar con la API.

Usar python-dotenv para cargar la URL base de la API desde .env.

Opcional: Autenticación con JWT o Basic Auth.

📂 Estructura Sugerida
/biblioteca-api
│── app.py             # API REST (Flask o Flask-RESTful)
│── routes/            # Rutas de la API
│── models/            # Modelos de datos
│── requirements.txt

/biblioteca-cliente
│── app.py             # Cliente Flask
│── templates/         # Vistas HTML
│── static/            # Archivos estáticos
│── .env               # Variables de entorno (API_URL)
│── requirements.txt

▶️ Ejecución Local
1. Clonar el repositorio
git clone https://github.com/tuusuario/biblioteca.git
cd biblioteca

2. Instalar dependencias
pip install -r requirements.txt

3. Configurar .env

Ejemplo en cliente Flask:

API_URL=http://localhost:5000

4. Ejecutar API REST
cd biblioteca-api
python app.py

5. Ejecutar Cliente Flask
cd biblioteca-cliente
python app.py

🌐 Producción

API y Cliente pueden desplegarse en servidores separados.

Recomendado: usar Gunicorn como WSGI server y Nginx como proxy inverso.
