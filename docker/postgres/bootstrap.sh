#!/bin/sh

set -eu


if [ "${USER_ROLE_OPERATION:-}" = "PROMOTE_TO_SERVICE_DELIVERY" ]; then
    : "${TARGET_USER_EMAIL:?TARGET_USER_EMAIL is required}"

    if [ "$PGDATABASE" != "penflow" ]; then
        echo "Refusing role change: expected PGDATABASE=penflow."
        exit 1
    fi

    echo "Promoting user to service_delivery..."

    UPDATED_USER="$(
        psql \
          --set=ON_ERROR_STOP=1 \
          --set=target_email="$TARGET_USER_EMAIL" \
          --tuples-only \
          --no-align <<'SQL'
UPDATE users
SET role = 'service_delivery'
WHERE lower(email) = lower(:'target_email')
RETURNING id || '|' || email || '|' || role;
SQL
    )"

    if [ -z "$UPDATED_USER" ]; then
        echo "No local user was found for the supplied email."
        echo "The user must log into PenFlow once before promotion."
        exit 1
    fi

    echo "Promoted local user: $UPDATED_USER"
    exit 0
fi

echo "Checking PenFlow application schema..."

SCHEMA_EXISTS="$(
  psql \
    --tuples-only \
    --no-align \
    --command="SELECT to_regclass('public.organisations') IS NOT NULL;"
)"

if [ "$SCHEMA_EXISTS" = "t" ]; then
    echo "PenFlow schema already exists. Skipping schema bootstrap."
else
    echo "Installing PenFlow schema..."

    psql \
      --set=ON_ERROR_STOP=1 \
      --single-transaction \
      --file=/bootstrap/schema.sql

    echo "PenFlow schema installed."
fi


echo "Creating Keycloak database role if required..."

psql \
  --set=ON_ERROR_STOP=1 \
  --set=kc_user="$KEYCLOAK_DB_USER" \
  --set=kc_password="$KEYCLOAK_DB_PASSWORD" \
  <<'SQL'
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L',
  :'kc_user',
  :'kc_password'
)
WHERE NOT EXISTS (
  SELECT 1
  FROM pg_roles
  WHERE rolname = :'kc_user'
)
\gexec
SQL


echo "Creating Keycloak database if required..."

psql \
  --set=ON_ERROR_STOP=1 \
  --set=kc_db="$KEYCLOAK_DB_NAME" \
  --set=kc_user="$KEYCLOAK_DB_USER" \
  <<'SQL'
SELECT format(
  'CREATE DATABASE %I OWNER %I',
  :'kc_db',
  :'kc_user'
)
WHERE NOT EXISTS (
  SELECT 1
  FROM pg_database
  WHERE datname = :'kc_db'
)
\gexec
SQL

echo "Database bootstrap complete."