import redis
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

_redis_client = None

def get_redis_client():
    """
    Establece y devuelve una conexión con el cliente Redis (KeyDB).
    Utiliza un patrón Singleton para reutilizar la conexión.
    """
    global _redis_client
    if _redis_client is None:
        try:
            host = os.getenv('KEYDB_HOST', 'localhost')
            port = int(os.getenv('KEYDB_PORT', 6379))
            password = os.getenv('KEYDB_PASSWORD')

            # Si la contraseña es None o vacía, no se pasa el argumento 'password'
            if password:
                _redis_client = redis.Redis(host=host, port=port, password=password, db=0, decode_responses=True)
            else:
                _redis_client = redis.Redis(host=host, port=port, db=0, decode_responses=True)

            _redis_client.ping() # Verifica la conexión
            print(f"Conectado a KeyDB en {host}:{port}")
        except redis.exceptions.ConnectionError as e:
            print(f"Error de conexión a KeyDB: {e}")
            _redis_client = None
        except ValueError:
            print("Error: El puerto de KeyDB en .env no es un número válido.")
            _redis_client = None
    return _redis_client

def close_db_connection():
    """Cierra la conexión con el cliente Redis (KeyDB) si está abierta."""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        print("Conexión a KeyDB cerrada.")

# Se ejecuta solo si este script es ejecutado directamente (para pruebas de conexión)
if __name__ == '__main__':
    client = get_redis_client()
    if client:
        print("Prueba de conexión exitosa.")
        # Ejemplo de uso
        client.set("test_key", "test_value")
        print(f"test_key: {client.get('test_key')}")
        client.delete("test_key")
    else:
        print("Fallo la conexión de prueba.")
    close_db_connection()