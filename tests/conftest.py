import psycopg
import pytest

from src.utils.db import get_connection


@pytest.fixture(scope="session")
def db():
    """Connection to the loaded database. Integration tests are skipped when it is unavailable."""
    try:
        connection = get_connection()
    except (psycopg.OperationalError, RuntimeError) as error:
        pytest.skip(f"Database not available: {error}")
    loaded = connection.execute(
        "SELECT EXISTS (SELECT 1 FROM audit.etl_run WHERE status = 'succeeded')"
    ).fetchone()[0]
    if not loaded:
        pytest.skip("No successful ETL run - run python -m src.pipeline first")
    # Rules that look up rejected rows read the run ID the pipeline normally sets.
    connection.execute("SELECT set_config('etl.run_id', '0', false)")
    yield connection
    connection.close()


@pytest.fixture
def rollback(db):
    """Run a test inside a savepoint that is always rolled back, so a failing
    statement cannot leave the shared connection in an aborted transaction."""
    with db.transaction(force_rollback=True):
        yield db
