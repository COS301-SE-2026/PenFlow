#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage:"
    echo "  $0 <db-password> <keycloak-db-password> <keycloak-admin-password> <rabbitmq-password>"
    exit 1
fi

DB_PASSWORD="$1"
KEYCLOAK_DB_PASSWORD="$2"
KEYCLOAK_ADMIN_PASSWORD="$3"
RABBITMQ_PASSWORD="$4"

: "${HIBP_API_KEY:?HIBP_API_KEY environment variable is required}"
: "${SHODAN_API_KEY:?SHODAN_API_KEY environment variable is required}"
: "${URLSCAN_API_KEY:?URLSCAN_API_KEY environment variable is required}"
: "${SMTP_PASSWORD:?SMTP_PASSWORD environment variable is required}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"

AWS_REGION="$(
    aws configure get region
)"

if [ -z "$AWS_REGION" ]; then
    AWS_REGION="af-south-1"
fi


echo "1. Checking prerequisites"

for command in terraform aws docker jq; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command"
        exit 1
    fi
done

aws sts get-caller-identity >/dev/null

echo "AWS authentication OK."
echo "Region: $AWS_REGION"


echo "2. Initializing Terraform"

terraform -chdir="$INFRA_DIR" init
terraform -chdir="$INFRA_DIR" validate


echo "3. Requesting ACM certificate"

terraform -chdir="$INFRA_DIR" apply \
    -auto-approve \
    -target=aws_acm_certificate.main \
    -var="db_password=$DB_PASSWORD" \
    -var="rabbitmq_password=$RABBITMQ_PASSWORD"


echo "4. DNS certificate validation"

echo ""
echo "Add these CNAME records to the DNS provider"
echo "managing the configured domain:"
echo ""

terraform -chdir="$INFRA_DIR" output \
    -json acm_validation_records |
    jq .

echo ""
read -r -p "Press Enter once all ACM validation records have been created..."

CERTIFICATE_ARN="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw acm_certificate_arn
)"

echo ""
echo "Waiting for ACM to validate:"
echo "$CERTIFICATE_ARN"

aws acm wait certificate-validated \
    --region "$AWS_REGION" \
    --certificate-arn "$CERTIFICATE_ARN"

echo "Certificate validated."


echo "5. Provisioning base infrastructure"

terraform -chdir="$INFRA_DIR" apply \
    -auto-approve \
    -var="db_password=$DB_PASSWORD" \
    -var="rabbitmq_password=$RABBITMQ_PASSWORD" \
    -var="backend_desired_count=0" \
    -var="frontend_desired_count=0" \
    -var="worker_desired_count=0" \
    -var="email_worker_desired_count=0" \
    -var="keycloak_desired_count=0" \
    -var="schedule_worker_desired_count=0" \
    -var="celery_beat_desired_count=0"


echo "6. Reading Terraform outputs"

CLUSTER="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw ecs_cluster_name
)"

BOOTSTRAP_TASK="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw db_bootstrap_task_definition_arn
)"

BOOTSTRAP_SG="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw db_bootstrap_security_group_id
)"

BACKEND_ECR="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw backend_ecr_repository_url
)"

FRONTEND_ECR="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw frontend_ecr_repository_url
)"

WORKER_ECR="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw worker_ecr_repository_url
)"

KEYCLOAK_ECR="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw keycloak_ecr_repository_url
)"

DB_BOOTSTRAP_ECR="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw db_bootstrap_ecr_repository_url
)"

mapfile -t SUBNETS < <(
    terraform -chdir="$INFRA_DIR" output \
        -json public_subnet_ids |
    jq -r '.[]'
)

if [ "${#SUBNETS[@]}" -eq 0 ]; then
    echo "Terraform returned no public subnets."
    exit 1
fi

SUBNET_LIST="$(IFS=,; echo "${SUBNETS[*]}")"


echo "7. Logging into Amazon ECR"

ECR_REGISTRY="${BACKEND_ECR%%/*}"

aws ecr get-login-password \
    --region "$AWS_REGION" |
    docker login \
        --username AWS \
        --password-stdin \
        "$ECR_REGISTRY"


echo "8. Building initial container images"

docker build \
    -f "$REPO_ROOT/docker/Dockerfile.backend" \
    -t "$BACKEND_ECR:latest" \
    "$REPO_ROOT"

docker build \
    -f "$REPO_ROOT/docker/Dockerfile.frontend" \
    -t "$FRONTEND_ECR:latest" \
    "$REPO_ROOT"

docker build \
    -f "$REPO_ROOT/docker/Dockerfile.workers" \
    -t "$WORKER_ECR:latest" \
    "$REPO_ROOT"

docker build \
    -f "$REPO_ROOT/docker/Dockerfile.keycloak" \
    -t "$KEYCLOAK_ECR:latest" \
    "$REPO_ROOT"

docker build \
    -f "$REPO_ROOT/docker/Dockerfile.db-bootstrap" \
    -t "$DB_BOOTSTRAP_ECR:latest" \
    "$REPO_ROOT"

echo "9. Pushing initial container images"

docker push "$BACKEND_ECR:latest"
docker push "$FRONTEND_ECR:latest"
docker push "$WORKER_ECR:latest"
docker push "$KEYCLOAK_ECR:latest"
docker push "$DB_BOOTSTRAP_ECR:latest"


echo "10. Populating Secrets Manager"

get_secret_arn() {
    local resource="$1"

    terraform -chdir="$INFRA_DIR" state show "$resource" |
        sed -n 's/^ *arn *= *"\(.*\)"/\1/p'
}

DB_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.db_password
)"

KC_DB_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.keycloak_db_password
)"

KC_ADMIN_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.keycloak_admin_password
)"

RABBIT_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.rabbitmq_password
)"

HIBP_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.hibp_api_key
)"

SHODAN_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.shodan_api_key
)"

URLSCAN_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.urlscan_api_key
)"

SMTP_SECRET_ARN="$(
    get_secret_arn aws_secretsmanager_secret.smtp_password
)"

for secret in \
    "$DB_SECRET_ARN" \
    "$KC_DB_SECRET_ARN" \
    "$KC_ADMIN_SECRET_ARN" \
    "$RABBIT_SECRET_ARN" \
    "$HIBP_SECRET_ARN" \
    "$SHODAN_SECRET_ARN" \
    "$URLSCAN_SECRET_ARN" \
    "$SMTP_SECRET_ARN"
do
    if [ -z "$secret" ]; then
        echo "Failed to resolve a Secrets Manager ARN."
        exit 1
    fi
done

aws secretsmanager put-secret-value \
    --secret-id "$DB_SECRET_ARN" \
    --secret-string "$DB_PASSWORD" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$KC_DB_SECRET_ARN" \
    --secret-string "$KEYCLOAK_DB_PASSWORD" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$KC_ADMIN_SECRET_ARN" \
    --secret-string "$KEYCLOAK_ADMIN_PASSWORD" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$RABBIT_SECRET_ARN" \
    --secret-string "$RABBITMQ_PASSWORD" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$HIBP_SECRET_ARN" \
    --secret-string "$HIBP_API_KEY" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$SHODAN_SECRET_ARN" \
    --secret-string "$SHODAN_API_KEY" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$URLSCAN_SECRET_ARN" \
    --secret-string "$URLSCAN_API_KEY" \
    >/dev/null

aws secretsmanager put-secret-value \
    --secret-id "$SMTP_SECRET_ARN" \
    --secret-string "$SMTP_PASSWORD" \
    >/dev/null

echo "Secrets populated."

echo "11. Bootstrapping Keycloak database"

TASK_ARN="$(
    aws ecs run-task \
        --region "$AWS_REGION" \
        --cluster "$CLUSTER" \
        --launch-type FARGATE \
        --task-definition "$BOOTSTRAP_TASK" \
        --network-configuration \
        "awsvpcConfiguration={subnets=[$SUBNET_LIST],securityGroups=[$BOOTSTRAP_SG],assignPublicIp=ENABLED}" \
        --query 'tasks[0].taskArn' \
        --output text
)"

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" = "None" ]; then
    echo "Failed to start database bootstrap task."
    exit 1
fi

echo "Bootstrap task:"
echo "$TASK_ARN"

aws ecs wait tasks-stopped \
    --region "$AWS_REGION" \
    --cluster "$CLUSTER" \
    --tasks "$TASK_ARN"

EXIT_CODE="$(
    aws ecs describe-tasks \
        --region "$AWS_REGION" \
        --cluster "$CLUSTER" \
        --tasks "$TASK_ARN" \
        --query 'tasks[0].containers[0].exitCode' \
        --output text
)"

STOPPED_REASON="$(
    aws ecs describe-tasks \
        --region "$AWS_REGION" \
        --cluster "$CLUSTER" \
        --tasks "$TASK_ARN" \
        --query 'tasks[0].stoppedReason' \
        --output text
)"

if [ "$EXIT_CODE" != "0" ]; then
    echo "Database bootstrap failed."
    echo "Exit code: $EXIT_CODE"
    echo "Stopped reason: $STOPPED_REASON"

    aws ecs describe-tasks \
        --region "$AWS_REGION" \
        --cluster "$CLUSTER" \
        --tasks "$TASK_ARN"

    exit 1
fi

echo "Database bootstrap succeeded."


echo "12. Starting PenFlow services"

terraform -chdir="$INFRA_DIR" apply \
    -auto-approve \
    -var="db_password=$DB_PASSWORD" \
    -var="rabbitmq_password=$RABBITMQ_PASSWORD" \
    -var="backend_desired_count=1" \
    -var="frontend_desired_count=1" \
    -var="worker_desired_count=1" \
    -var="email_worker_desired_count=1" \
    -var="keycloak_desired_count=1" \
    -var="schedule_worker_desired_count=1" \
    -var="celery_beat_desired_count=1"


echo "13. Deployment information"

ALB_DNS="$(
    terraform -chdir="$INFRA_DIR" output \
        -raw alb_dns_name
)"

echo "PenFlow infrastructure bootstrap complete"