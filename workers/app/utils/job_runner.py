import os 
import json 
import logging 
import docker 
import boto3 
from typing import Any 

logger = logging.getLogger(__name__) 

ALLOWED_ENV_VARS = {
    "BACKEND_URL", "BACKEND_API_URL", "SCAN_MODE", 
    "URLSCAN_API_KEY", "SHODAN_API_KEY", "HUNTER_API_KEY", "HIBP_API_KEY"
}

def dispatch_scan_job(tool_name: str, payload: dict[str, Any]) -> bool: 
    environment = os.getenv("ENVIRONMENT", "local")
    command = ["python", "-m", "app.cli", tool_name, "--payload", json.dumps(payload)]

    if environment == "production": 
        return _run_fargate_task(command)
    else:
        env_vars = {k: v for k, v in os.environ.item() if k in ALLOWED_ENV_VARS}
        return _run_local_docker_container(command, env_vars) 
