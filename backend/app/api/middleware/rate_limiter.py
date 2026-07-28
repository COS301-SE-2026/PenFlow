import os
from slowapi import Limiter
from slowapi.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL
)