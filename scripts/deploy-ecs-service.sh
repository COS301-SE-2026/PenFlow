#!/usr/bin/env bash

set -euo pipefail

CLUSTER="$1"
SERVICE="$2"
CONTAINER="$3"
IMAGE="$4"


CURRENT_TASK_DEFINITION="$(
    aws ecs describe-services \
        --cluster "$CLUSTER" \
        --services "$SERVICE" \
        --query 'services[0].taskDefinition' \
        --output text
)"

if (
    [ -z "$CURRENT_TASK_DEFINITION" ] ||
    [ "$CURRENT_TASK_DEFINITION" = "None" ]
); then
    echo "Unable to find current task definition for $SERVICE"
    exit 1
fi

echo "Current task definition: $CURRENT_TASK_DEFINITION"

aws ecs describe-task-definition \
    --task-definition "$CURRENT_TASK_DEFINITION" \
    --query 'taskDefinition' \
    > current-task-definition.json

if ! jq -e \
    --arg container "$CONTAINER" \
    '.containerDefinitions | any(.name == $container)' \
    current-task-definition.json >/dev/null; then

    echo "Container '$CONTAINER' does not exist in task definition:"
    echo "$CURRENT_TASK_DEFINITION"
    exit 1
fi

jq \
    --arg container "$CONTAINER" \
    --arg image "$IMAGE" \
    '
        del(
            .taskDefinitionArn,
            .revision,
            .status,
            .requiresAttributes,
            .compatibilities,
            .registeredAt,
            .registeredBy,
            .deregisteredAt,
            .deleteRequestedAt
        )
        |
        .containerDefinitions |= map(
            if .name == $container
            then .image = $image
            else .
            end
        )
    ' \
    current-task-definition.json \
    > new-task-definition.json

NEW_TASK_DEFINITION="$(
    aws ecs register-task-definition \
        --cli-input-json file://new-task-definition.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text
)"

if [ -z "$NEW_TASK_DEFINITION" ]; then
    echo "Failed to register the new task definition"
    exit 1
fi

echo "Registered task definition:"
echo "$NEW_TASK_DEFINITION"

aws ecs update-service \
    --cluster "$CLUSTER" \
    --service "$SERVICE" \
    --task-definition "$NEW_TASK_DEFINITION" \
    --output json >/dev/null

echo "ECS service updated"
echo "Waiting for service stability"

aws ecs wait services-stable \
    --cluster "$CLUSTER" \
    --services "$SERVICE"

echo "$SERVICE is stable"