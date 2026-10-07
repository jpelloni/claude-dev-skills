# Database rules

- The database is PostgreSQL 16.
- Every Alembic upgrade has a real downgrade that restores the previous schema.
- Indexes on existing tables use `CREATE INDEX CONCURRENTLY` and must not run inside a transaction.
- Do not apply migrations or edit migration files unless I ask.
