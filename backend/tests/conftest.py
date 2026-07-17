import pytest

from app.api.dependencies import get_operator_session, require_admin_csrf, require_admin_session, require_operator_csrf
from app.api.main import app
from app.core.security import OperatorSession


@pytest.fixture(autouse=True)
def authenticated_operator_for_api_tests():
    session = OperatorSession(
        email="test-operator@example.com",
        csrf_token="test-csrf-token",
        expires_at=4_102_444_800,
    )
    app.dependency_overrides[get_operator_session] = lambda: session
    app.dependency_overrides[require_operator_csrf] = lambda: session
    app.dependency_overrides[require_admin_session] = lambda: session
    app.dependency_overrides[require_admin_csrf] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_operator_session, None)
        app.dependency_overrides.pop(require_operator_csrf, None)
        app.dependency_overrides.pop(require_admin_session, None)
        app.dependency_overrides.pop(require_admin_csrf, None)
