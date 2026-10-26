\set ON_ERROR_STOP on
\getenv runtime_password APP_DATABASE_PASSWORD

BEGIN;

SELECT format(
    'CREATE ROLE penflow_runtime LOGIN PASSWORD %L
     NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'runtime_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'penflow_runtime'
)
\gexec

SELECT format(
    'ALTER ROLE penflow_runtime PASSWORD %L',
    :'runtime_password'
)
\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO penflow_runtime',
    current_database()
)
\gexec

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO penflow_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public TO penflow_runtime;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public TO penflow_runtime;

REVOKE ALL ON TABLE public.audit_logs FROM PUBLIC;
REVOKE ALL ON TABLE public.audit_logs FROM penflow_runtime;
GRANT SELECT, INSERT ON TABLE public.audit_logs TO penflow_runtime;

CREATE OR REPLACE FUNCTION public.reject_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'Audit records are append-only'
        USING ERRCODE = '42501';
END;
$$;

DROP TRIGGER IF EXISTS audit_logs_no_mutation
ON public.audit_logs;

CREATE TRIGGER audit_logs_no_mutation
BEFORE UPDATE OR DELETE ON public.audit_logs
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_audit_mutation();

DROP TRIGGER IF EXISTS audit_logs_no_truncate
ON public.audit_logs;

CREATE TRIGGER audit_logs_no_truncate
BEFORE TRUNCATE ON public.audit_logs
FOR EACH STATEMENT
EXECUTE FUNCTION public.reject_audit_mutation();

COMMIT;