# path: ./db_manager.py

from psycopg2.pool import SimpleConnectionPool
from psycopg2 import sql, OperationalError
from gui import DB_CONFIG
from log_manager import LogManager
from threading import Lock

logger = LogManager("DBManager")

class DBManager:
    """Manages a thread-safe database connection pool and ensures the required table exists."""
    _db_pool = None
    _lock = Lock()

    @classmethod
    def initialize_db(cls):
        """
        Initialize the database connection pool and ensure the required table exists.
        """
        with cls._lock:
            if cls._db_pool is None:
                try:
                    cls._db_pool = SimpleConnectionPool(
                        minconn=1,
                        maxconn=20,
                        dbname=DB_CONFIG["dbname"],
                        user=DB_CONFIG["user"],
                        password=DB_CONFIG["password"],
                        host=DB_CONFIG["host"],
                        port=DB_CONFIG["port"],
                    )
                    logger.info("Database connection pool established successfully.")

                    # Ensure the required table exists
                    cls._ensure_table_exists()

                except OperationalError as e:
                    logger.error(f"Database connection error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Failed to establish database connection pool: {e}")
                    raise
            else:
                logger.warning("Database pool has already been initialized.")

    @classmethod
    def _ensure_table_exists(cls):
        """
        Ensure the 'mario_env_stats' table exists in the database.
        """
        create_table_query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS mario_env_stats (
            id SERIAL PRIMARY KEY,
            env_id INT NOT NULL,
            world INT NOT NULL,
            stage INT NOT NULL,
            area INT DEFAULT 0,
            x_position INT NOT NULL,
            y_position INT NOT NULL,
            score INT NOT NULL,
            coins INT NOT NULL,
            life INT DEFAULT 0,
            status VARCHAR(50) NOT NULL,
            player_state VARCHAR(50) NOT NULL,
            flag_get BOOLEAN DEFAULT FALSE,
            additional_info JSONB,
            step INT DEFAULT 0,
            episode INT DEFAULT 0
        );
        """)
        conn = None
        try:
            conn = cls.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(create_table_query)
                conn.commit()
        except Exception as e:
            logger.error(f"Error ensuring table existence: {e}")
            raise
        finally:
            if conn:
                cls.release_connection(conn)

    @classmethod
    def get_connection(cls):
        """
        Get a database connection from the pool.
        """
        if cls._db_pool is None:
            raise ValueError("Database pool is not initialized. Call 'initialize_db()' first.")
        try:
            return cls._db_pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get a connection from the pool: {e}")
            raise

    @classmethod
    def release_connection(cls, conn):
        """
        Release a database connection back to the pool.
        """
        if cls._db_pool is None:
            logger.warning("Database pool is not initialized. Cannot release connection.")
            return
        try:
            cls._db_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to release connection back to the pool: {e}")

    @classmethod
    def close_db_pool(cls):
        """
        Close the database connection pool.
        """
        with cls._lock:
            if cls._db_pool:
                try:
                    cls._db_pool.closeall()
                    cls._db_pool = None
                    logger.info("Database connection pool closed.")
                except Exception as e:
                    logger.error(f"Error closing the database connection pool: {e}")
