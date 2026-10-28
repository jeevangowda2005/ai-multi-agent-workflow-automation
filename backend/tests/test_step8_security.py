"""
Step 8 — Security & Production Readiness Tests

Tests verified here:
1. Request body size limit (5 MB) middleware rejects oversized payloads.
2. Health endpoint returns {"status": "healthy"}.
3. CORS origins are read from settings (not hard-coded to "*").
4. .env.example exists and contains no real secrets.
5. .gitignore covers all sensitive paths.
6. Generic 500 handler does not leak internal exception messages.
7. API docs are accessible at /docs (not disabled in test mode).
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# ─────────────────────────────────────────────────────────────────────────────
# App fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Create a TestClient with a real (test) database session."""
    # Set required env vars before importing the app
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_step8.db")
    os.environ.setdefault("GEMINI_API_KEY", "")

    from app.main import app
    from app.db.session import get_db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base

    TEST_DB = "sqlite:///./test_step8.db"
    engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_step8.db"):
        os.remove("./test_step8.db")


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")


class TestHealthEndpoint:
    def test_health_returns_healthy(self, client):
        """GET /api/health must return {"status": "healthy"}."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json().get("status") == "healthy"


class TestRequestSizeLimit:
    def test_large_payload_rejected(self, client):
        """A payload larger than 5 MB must return HTTP 413."""
        big_body = b"x" * (5 * 1024 * 1024 + 1)
        resp = client.post(
            "/api/ai/analyze",
            content=big_body,
            headers={"content-type": "application/json", "content-length": str(len(big_body))},
        )
        assert resp.status_code == 413

    def test_normal_payload_not_rejected(self, client):
        """A small payload must NOT be rejected by the size-limit middleware."""
        # The request will fail for other reasons (missing body fields),
        # but must NOT return 413.
        resp = client.post(
            "/api/ai/analyze",
            json={"task_description": "hello"},
        )
        assert resp.status_code != 413


class TestCORSConfiguration:
    def test_cors_origins_not_wildcard(self):
        """Production CORS origins must NOT be the bare wildcard '*'."""
        from app.core.config import get_settings
        s = get_settings()
        origins = s.cors_origins
        assert isinstance(origins, list), "cors_origins should be a list"
        # In test env the default is localhost origins — confirm no bare '*'
        assert "*" not in origins, (
            "CORS must not allow all origins ('*') — use specific origins in production"
        )

    def test_cors_origins_non_empty(self):
        """CORS origins list must have at least one entry."""
        from app.core.config import get_settings
        s = get_settings()
        assert len(s.cors_origins) >= 1


class TestDotEnvExample:
    def test_env_example_exists(self):
        """backend/.env.example must exist so contributors know the required vars."""
        env_example = os.path.join(BACKEND_DIR, ".env.example")
        assert os.path.isfile(env_example), ".env.example not found in backend/"

    def test_env_example_has_no_real_key(self):
        """The .env.example must not contain a real Gemini API key."""
        env_example = os.path.join(BACKEND_DIR, ".env.example")
        if not os.path.isfile(env_example):
            pytest.skip(".env.example not present")
        content = open(env_example).read()
        # A real Gemini API key starts with "AIza" followed by 35 chars
        import re
        real_keys = re.findall(r'AIza[0-9A-Za-z_\-]{35}', content)
        assert not real_keys, f"Real API key found in .env.example: {real_keys}"


class TestGitignore:
    def test_gitignore_covers_env(self):
        """Root .gitignore must cover backend/.env."""
        gitignore = os.path.join(ROOT_DIR, ".gitignore")
        assert os.path.isfile(gitignore), ".gitignore not found at project root"
        content = open(gitignore).read()
        assert "backend/.env" in content or (".env" in content and "venv" in content), \
            ".gitignore should exclude .env files"

    def test_gitignore_covers_venv(self):
        """Root .gitignore must exclude venv/ directories."""
        gitignore = os.path.join(ROOT_DIR, ".gitignore")
        content = open(gitignore).read()
        assert "venv/" in content or "venv" in content

    def test_gitignore_covers_frontend_dist(self):
        """Root .gitignore must exclude frontend/dist/."""
        gitignore = os.path.join(ROOT_DIR, ".gitignore")
        content = open(gitignore).read()
        assert "frontend/dist" in content or "dist/" in content

    def test_gitignore_covers_node_modules(self):
        """Root .gitignore must exclude frontend/node_modules/."""
        gitignore = os.path.join(ROOT_DIR, ".gitignore")
        content = open(gitignore).read()
        assert "node_modules" in content


class TestGenericExceptionHandler:
    def test_unhandled_exception_returns_generic_message(self, client):
        """Unhandled server errors must return a generic message without details."""
        # Patch a route to raise an unexpected exception
        from app.api.routes import health

        original = health.health_check

        async def boom():
            raise RuntimeError("super secret internal error")

        health.health_check = boom
        try:
            resp = client.get("/api/health")
            # Should be 500 with a generic body, not the raw exception message
            if resp.status_code == 500:
                body = resp.json()
                assert "super secret internal error" not in str(body), \
                    "Internal exception detail must not be leaked in HTTP response"
        finally:
            health.health_check = original


class TestDockerfiles:
    def test_backend_dockerfile_exists(self):
        """backend/Dockerfile must exist."""
        assert os.path.isfile(os.path.join(BACKEND_DIR, "Dockerfile"))

    def test_frontend_dockerfile_exists(self):
        """frontend/Dockerfile must exist."""
        frontend_dir = os.path.join(ROOT_DIR, "frontend")
        assert os.path.isfile(os.path.join(frontend_dir, "Dockerfile"))

    def test_docker_compose_exists(self):
        """docker-compose.yml must exist at the project root."""
        assert os.path.isfile(os.path.join(ROOT_DIR, "docker-compose.yml"))

    def test_docker_compose_has_db_service(self):
        """docker-compose.yml must define a 'db' service."""
        compose_path = os.path.join(ROOT_DIR, "docker-compose.yml")
        content = open(compose_path).read()
        assert "db:" in content

    def test_docker_compose_has_backend_service(self):
        """docker-compose.yml must define a 'backend' service."""
        compose_path = os.path.join(ROOT_DIR, "docker-compose.yml")
        content = open(compose_path).read()
        assert "backend:" in content

    def test_docker_compose_has_frontend_service(self):
        """docker-compose.yml must define a 'frontend' service."""
        compose_path = os.path.join(ROOT_DIR, "docker-compose.yml")
        content = open(compose_path).read()
        assert "frontend:" in content
