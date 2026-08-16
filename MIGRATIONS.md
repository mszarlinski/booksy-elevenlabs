# Database Migrations Guide

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema management with async SQLAlchemy support.

## Setup

Alembic is already configured in the project. All migration files are stored in the `alembic/` directory, with revision scripts in `alembic/versions/`.

## Configuration

- **Database Connection**: Uses the `DATABASE_URL` environment variable from `.env`
- **Async Support**: Configured for PostgreSQL with asyncpg driver
- **ORM Models**: Metadata is sourced from `app/database.Base` and automatically picks up all models registered in `app/models.py`

## Common Commands

### Check Current Migration Status
```bash
uv run alembic current
```

### View Migration History
```bash
uv run alembic history --oneline
```

### Upgrade Database to Latest Migration
```bash
uv run alembic upgrade head
```

### Upgrade Database to Specific Revision
```bash
uv run alembic upgrade <revision_id>
```

### Downgrade Database by One Revision
```bash
uv run alembic downgrade -1
```

### Downgrade to Specific Revision
```bash
uv run alembic downgrade <revision_id>
```

### Generate New Migration (Auto-detect Schema Changes)
After modifying ORM models in `app/models.py`, generate a migration:
```bash
uv run alembic revision --autogenerate -m "Descriptive message of changes"
```

### Generate Empty Migration (for Custom SQL)
```bash
uv run alembic revision -m "Descriptive message"
```

### Review Migration Script Before Applying
Open the generated file in `alembic/versions/` to review the SQL changes before applying:
```bash
uv run alembic upgrade head --sql  # Dry-run: view SQL without executing
```

## Migration Files

Each migration file contains:
- **upgrade()**: Applies the schema changes
- **downgrade()**: Reverts the schema changes

Migration files are automatically generated with revision IDs (e.g., `755a0269244c_create_initial_tables.py`).

## Best Practices

1. **Review Auto-Generated Migrations**: Always review auto-generated migrations before committing, as Alembic may not perfectly detect all changes.

2. **Make Migrations Idempotent**: Ensure migrations can be safely re-run without errors.

3. **Test Before Committing**: 
   - Test upgrade: `uv run alembic upgrade head`
   - Test downgrade: `uv run alembic downgrade -1`
   - Test upgrade again to verify

4. **Commit Migrations with Code**: Commit migration files alongside model changes in git.

5. **Use Descriptive Messages**: Use clear, descriptive messages when creating migrations:
   ```bash
   uv run alembic revision --autogenerate -m "Add created_at column to businesses table"
   ```

## Initial Migration

The initial migration (`755a0269244c_create_initial_tables_business_employee_.py`) creates all core tables:

- **businesses**: Business/organization data
- **employees**: Employee information linked to businesses
- **services**: Services offered by businesses
- **bookings**: Customer bookings linking services and employees

All tables use string UUIDs (36-character) as primary keys and have proper foreign key constraints with cascade delete.

## Troubleshooting

### Migration Fails Due to Connection Error
- Verify PostgreSQL is running: `docker ps | grep postgres`
- Check `DATABASE_URL` in `.env` file
- Ensure credentials match your PostgreSQL setup

### Auto-generate Doesn't Detect Changes
- Verify model changes are properly saved in `app/models.py`
- Check that models inherit from `Base` (imported from `app.database`)
- Ensure models are imported in `app/__init__.py`

### Need to Rollback Production Migration
```bash
uv run alembic downgrade <previous_revision_id>
```

## Running Migrations in Production

For production deployments, use:
```bash
uv run alembic upgrade head
```

This should be run as part of your deployment pipeline before starting the application.
