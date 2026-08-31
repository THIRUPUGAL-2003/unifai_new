-- FIT2CLOUD creates: database=Unifai_test, user=Unifai_test, password=YP2025-2026yp
-- Run in pgAdmin as admin if permissions are missing:

GRANT ALL PRIVILEGES ON DATABASE "Unifai_test" TO "Unifai_test";

\c "Unifai_test"

GRANT ALL ON SCHEMA public TO "Unifai_test";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "Unifai_test";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "Unifai_test";
