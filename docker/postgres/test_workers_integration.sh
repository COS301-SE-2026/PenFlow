#!/bin/sh
set -e

docker compose up -d postgres-test rabbitmq

docker compose build workers-test

docker compose run --rm workers-test pytest tests/integration

# Comment this out if you want containers to stay up after integration tests are run
docker compose down -v --remove-orphans