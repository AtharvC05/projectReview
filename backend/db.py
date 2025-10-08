import os
import logging
import mysql.connector

logger = logging.getLogger(__name__)


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


def get_db_config():
    """Return database connection configuration from environment with defaults.

    Env vars: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
    Defaults: localhost/root/1234/project_review1
    """
    return {
        "host": _read_env("DB_HOST", "localhost"),
        "user": _read_env("DB_USER", "root"),
        "password": _read_env("DB_PASSWORD", "1234"),
        "database": _read_env("DB_NAME", "testing"),
        "autocommit": True,
    }


def connect_db(database: str | None = None):
    """Create and return a MySQL connection.

    If `database` is provided, it overrides the DB_NAME env var/default.
    """
    config = get_db_config()
    if database:
        config["database"] = database
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        raise


