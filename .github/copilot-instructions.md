# AI Coding Agent Instructions

## Project Overview
This project is a FastAPI-based backend application with PostgreSQL as the database. It is designed for asynchronous operations and includes features like JWT-based authentication, user management, and token refresh mechanisms. The project is containerized using Docker and follows modern Python development practices with tools like Poetry, Alembic, and pre-commit hooks.

## Architecture
- **FastAPI**: The main framework for building APIs.
- **SQLAlchemy**: Used for database interactions with async support.
- **Alembic**: Handles database migrations.
- **JWT Authentication**: Implemented for secure user authentication.
- **Docker**: Used for containerization and local development.
- **Testing**: Pytest is used for unit and integration tests.

### Key Directories
- `app/`: Contains the main application code.
  - `api/`: API endpoints and dependencies.
  - `core/`: Core utilities like configuration, database sessions, and security.
  - `schemas/`: Pydantic models for request and response validation.
  - `tests/`: Test cases for the application.
- `alembic/`: Database migration scripts.

## Developer Workflows

### Setting Up the Project
1. Install dependencies:
   ```bash
   poetry install
   ```
2. Start the database:
   ```bash
   docker-compose up -d
   ```
3. Run migrations:
   ```bash
   alembic upgrade head
   ```
4. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

### Running Tests
- Run all tests:
  ```bash
  pytest
  ```
- Test configuration is defined in `pyproject.toml`.

### Pre-commit Hooks
- Install pre-commit hooks:
  ```bash
  pre-commit install --install-hooks
  ```
- Run hooks on all files:
  ```bash
  pre-commit run --all-files
  ```

## Project-Specific Conventions
- **JWT Tokens**: Created and verified using `app.core.security.jwt`.
- **Database Sessions**: Managed using `app.core.database_session`.
- **Environment Variables**: Defined in `.env` and loaded via `pydantic-settings`.
- **Testing**: Tests use isolated databases created dynamically in `conftest.py`.
- **Schemas**: Requests and responses are defined in `schemas/requests.py` and `schemas/responses.py`.

## Integration Points
- **Database**: PostgreSQL is used with asyncpg driver. Connection details are configured in `app/core/config.py`.
- **Docker**: The `Dockerfile` and `docker-compose.yml` are configured for local development.
- **CI/CD**: GitHub Actions workflows are defined for testing (`tests.yml`) and type checking (`type_check.yml`).

## Examples

### Adding a New Endpoint
1. Define the route in `app/api/endpoints/`.
2. Add request and response schemas in `schemas/`.
3. Include the route in `api_router` in `app/api/api_router.py`.
4. Write tests in the appropriate `tests/` subdirectory.

### Creating a Database Migration
1. Generate a migration:
   ```bash
   alembic revision --autogenerate -m "Migration message"
   ```
2. Apply the migration:
   ```bash
   alembic upgrade head
   ```

## Notes
- Follow the existing patterns for dependency injection using FastAPI's `Depends`.
- Ensure 100% test coverage as enforced by the `pytest-cov` plugin.
- Use `ruff` for linting and formatting.

For more details, refer to the `README.md` and the codebase.