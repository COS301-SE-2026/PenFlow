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

def _run_fargate_task(command: list[str]) -> bool: 
    cluster = os.getenv("ECS_CLUSTER_NAME") 
    task_definition = os.getenv("ECS_TASK_DEFINITION")
    subnets = [s for s in os.getenv("ECS_SUBNETS", "").split(",") if s]
    security_groups = [s for s in os.getenv("ECS_SECURITY_GROUPS", "").split(",") if s]
    assign_public_ip = os.getenv("ECS_ASSIGN_PUBLIC_IP", "DISABLED")

    if not subnets or not security_groups: 
        logger.error("Missing ECS_SUBNETS or ECS_SECURITY_GROUPS")
        return False 

    client = boto3.client('ecs', region_name=os.getenv("AWS_REGION", "af-south-1"))
    logger.info(f"Dispatching Fargate task for: {command[3]}")

    try:
        response = client.run_task(
            cluster=cluster,
            taskDefinition=task_definition,
            launchType='FARGATE', 
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': subnets, 
                    'securityGroups': security_groups,
                    'assignPublicIp': assign_public_ip
                }
            }, 
            overrides={
                'containerOverrides': [{
                    'name': 'penflow-worker',
                    'command': command
                }]
            }
        )

        if not response.get('tasks'): 
            logger.error(f"Fargate run_task failed: {response.get('failures', [])}")
            return False 

        task_arn = response['tasks'][0]['taskArn']
        waiter = client.get_waiter('tasks_stopped')
        waiter.wait(cluster=cluster, task=[task_arn])

        task_info = client.describe_tasks(cluster=cluster, tasks=[task_arn])
        exit_code = task_info['tasks'][0]['containers'][0].get('exitCode')

        return exit_code == 0 
    except Exception as e:
        logger.error(f"Fargate dispatch failed: {e}")
        return False

def _run_local_docker_container(command: list[str], env_vars: dict[str, str]) -> bool:
    client = docker.from_env() 
    image_name = os.getenv("WORKER_IMAGE", "penflow-worker:local")
    network_name = os.getenv("DOCKER_NETWORK", "penflow-network")

    container = None 
    logger.info(f"Dispatching Local Docker container for: {command[3]}")
    try:
        container = client.containers.run(
            image=image_name, 
            command=command, 
            environment=env_vars, 
            network=network_name, 
            detach=True,
        )
        result = container.wait()
        return result.get('StatusCode') == 0 
    except Exception as e: 
        logger.error(f"Local Docker dispatch failed: {e}")
        return False
    finally:
        if container: 
            try: 
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")