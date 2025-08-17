from celery import Celery
import os
from dotenv import load_dotenv

# Cargar variables de entorno para Celery
load_dotenv()

def make_celery(app=None):
    """
    Crea y configura una instancia de Celery.
    Si se le pasa una aplicación Flask, configura Celery para que use el contexto de la aplicación.
    """
    celery_app = Celery(
        __name__,
        broker=os.getenv('CELERY_BROKER_URL'),
        backend=os.getenv('CELERY_RESULT_BACKEND')
    )

    # Configuración adicional de Celery (opcional)
    celery_app.conf.update(
        task_track_started=True, # Permite que las tareas reporten su estado como 'STARTED'
        broker_connection_retry_on_startup=True, # Reintentar conexión al broker al iniciar
        timezone='America/Panama', # Establece tu zona horaria (ajusta si es necesario)
        enable_utc=True, # Trabajar con UTC internamente
    )

    if app:
        # Configura Celery para que las tareas se ejecuten dentro del contexto de la aplicación Flask.
        # Esto es necesario si las tareas necesitan acceder a la configuración de Flask (como Flask-Mail).
        class ContextTask(celery_app.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery_app.Task = ContextTask
    return celery_app

# Este bloque solo es para que el archivo sea un módulo Celery válido y pueda ser importado.
# La instancia 'celery' real se crea en app.py al pasarle la app de Flask.
celery = make_celery()