import redis
import logging
import os
import celery
import kombu
from typing import Optional, Dict, Any

from ai_orchestration.core.config import (
    CELERY_BROKER_URL, REDIS_MAX_CONNECTIONS,
    REDIS_SOCKET_TIMEOUT, REDIS_RETRY_ON_TIMEOUT
)

logger = logging.getLogger("SnLag_RedisManager")

class RedisConnectionManager:
    """
    Requirement 3 & 4: Centralized Redis Connection Manager
    Handles pooled connections, capability detection, and protocol selection.
    """
    _instance: Optional['RedisConnectionManager'] = None
    _pool: Optional[redis.ConnectionPool] = None

    # Capability Cache
    server_version: Optional[str] = None
    negotiated_protocol: int = 2
    client_version: str = redis.__version__

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConnectionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self.server_version:
            self.audit_capabilities()
        if not self._pool:
            self.initialize_pool()

    def audit_capabilities(self):
        """
        Requirement 1: Audit Redis Version
        Detects server version and selects correct RESP protocol.
        """
        logger.info("Redis Manager: Auditing server capabilities...")

        # 1. Try to connect with RESP2 (safe for all versions)
        try:
            # We use a temporary client to check INFO
            temp_pool = redis.ConnectionPool.from_url(
                CELERY_BROKER_URL,
                protocol=2,
                socket_timeout=5,
                max_connections=1
            )
            temp_client = redis.Redis(connection_pool=temp_pool)

            info = temp_client.info()
            self.server_version = info.get("redis_version", "0.0.0")

            # Requirement 1: Protocol selection logic
            major_version = int(self.server_version.split('.')[0])
            if major_version >= 6:
                # If server is 6+, we COULD use RESP3, but for stability we might prefer 2
                # unless explicitly configured.
                # Per Requirement 1: "Allow RESP3 when supported"
                self.negotiated_protocol = 3
            else:
                self.negotiated_protocol = 2

            logger.info(f"Redis Manager: Detected Server v{self.server_version}. Selecting RESP{self.negotiated_protocol}.")
            temp_pool.disconnect()

        except Exception as e:
            logger.error(f"Redis Manager: Capability audit failed: {e}")
            # Fallback to safe defaults
            self.server_version = "Unknown"
            self.negotiated_protocol = 2

    def initialize_pool(self):
        """Requirement 4: Create pooled connections with selected protocol"""
        try:
            kwargs = {
                "max_connections": REDIS_MAX_CONNECTIONS,
                "socket_timeout": REDIS_SOCKET_TIMEOUT,
                "retry_on_timeout": REDIS_RETRY_ON_TIMEOUT,
                "decode_responses": False,
                "protocol": self.negotiated_protocol
            }

            self._pool = redis.ConnectionPool.from_url(CELERY_BROKER_URL, **kwargs)
            logger.info(f"Redis Manager: Connection pool initialized (RESP{self.negotiated_protocol}).")
        except Exception as e:
            logger.error(f"Redis Manager: Pool initialization failed: {e}")
            raise

    def get_client(self) -> redis.Redis:
        """Returns a managed Redis client"""
        if not self._pool:
            self.initialize_pool()
        return redis.Redis(connection_pool=self._pool)

    def get_diagnostics(self) -> Dict[str, Any]:
        """Requirement 5: Startup Diagnostics Data"""
        return {
            "redis_server": self.server_version,
            "redis_client": self.client_version,
            "negotiated_resp": f"RESP{self.negotiated_protocol}",
            "celery_version": celery.__version__,
            "kombu_version": kombu.__version__,
            "broker_url": CELERY_BROKER_URL.split('@')[-1] # Mask credentials
        }

    def check_health(self) -> bool:
        try:
            return self.get_client().ping()
        except:
            return False

# Singleton
redis_manager = RedisConnectionManager()
