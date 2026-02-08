"""
Testy pro zvýšení code coverage – error_codes, context_utils, permissions, DBFeeder, Dataloaders.

Spuštění s reportem coverage:
    pytest tests/test_coverage.py -v --cov=src --cov-report=term-missing
    pytest tests/ -m "not integration" -v --cov=src --cov-report=term-missing
    pytest tests/ -m "not integration" --cov=src --cov-report=html   # → složka htmlcov/
"""
import uuid
from unittest.mock import MagicMock

import pytest

from src.error_codes import (
    ERROR_CODES,
    get_error_info,
    format_error_message,
)
from src.GraphTypeDefinitions.context_utils import (
    ensure_user_in_context,
    get_user_id,
)


# --- error_codes ---


def test_get_error_info_known_code():
    """Známý kód vrací kategorii a popis."""
    code = uuid.UUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c5d")
    category, description = get_error_info(code)
    assert category == "OPRÁVNĚNÍ_ZAMÍTNUTO"
    assert "zápůjčky" in description


def test_get_error_info_unknown_code():
    """Neznámý kód vrací NEZNÁMÁ_CHYBA."""
    code = uuid.UUID("00000000-0000-0000-0000-000000000000")
    category, description = get_error_info(code)
    assert category == "NEZNÁMÁ_CHYBA"
    assert "neznámé" in description.lower()


def test_format_error_message_without_context():
    """Formátování zprávy bez dodatečného kontextu."""
    code = uuid.UUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d71")
    msg = format_error_message(code)
    assert "[NENALEZENO]" in msg
    assert "Majetek nebyl nalezen" in msg


def test_format_error_message_with_context():
    """Formátování zprávy s dodatečným kontextem."""
    code = uuid.UUID("2b1c2d3e-4f5a-4b6c-7d8e-9f0a1b2c3d4e")
    msg = format_error_message(code, additional_context="tabulka assets")
    assert "[CHYBA_DATABÁZE]" in msg
    assert "tabulka assets" in msg


def test_error_codes_dict_non_empty():
    """ERROR_CODES obsahuje očekávané záznamy."""
    assert len(ERROR_CODES) >= 1
    for code, (category, description) in ERROR_CODES.items():
        assert isinstance(code, uuid.UUID)
        assert isinstance(category, str)
        assert isinstance(description, str)


# --- context_utils ---


def test_ensure_user_in_context_from_user():
    """ensure_user_in_context vrací user z context['user']."""
    user = {"id": "user-123"}
    info = MagicMock()
    info.context = {"user": user}
    result = ensure_user_in_context(info)
    assert result == user
    assert result["id"] == "user-123"


def test_ensure_user_in_context_from_fallback():
    """ensure_user_in_context používá __original_user jako fallback."""
    fallback = {"id": "fallback-456"}
    info = MagicMock()
    info.context = {"user": None, "__original_user": fallback}
    result = ensure_user_in_context(info)
    assert result is not None
    assert result["id"] == "fallback-456"
    assert info.context["user"]["id"] == "fallback-456"


def test_ensure_user_in_context_no_user():
    """ensure_user_in_context vrací None když není user ani fallback."""
    info = MagicMock()
    info.context = {}
    result = ensure_user_in_context(info)
    assert result is None


def test_get_user_id_from_context():
    """get_user_id vrací UUID z kontextu."""
    user = {"id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}
    info = MagicMock()
    info.context = {"user": user}
    result = get_user_id(info)
    assert result == uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d")


def test_get_user_id_no_user():
    """get_user_id vrací None když není user."""
    info = MagicMock()
    info.context = {}
    result = get_user_id(info)
    assert result is None


def test_get_user_id_invalid_uuid():
    """get_user_id vrací None pro neplatné UUID v user id."""
    info = MagicMock()
    info.context = {"user": {"id": "not-a-uuid"}}
    result = get_user_id(info)
    assert result is None


def test_ensure_user_in_context_from_request_bearer():
    """ensure_user_in_context vytvoří user z Authorization: Bearer <token>."""
    info = MagicMock()
    info.context = {"user": None, "request": None}
    request = MagicMock()
    request.headers = {"Authorization": "Bearer my-token-123"}
    info.context["request"] = request
    result = ensure_user_in_context(info)
    assert result is not None
    assert result["id"] == "my-token-123"
    assert info.context["user"]["id"] == "my-token-123"


def test_ensure_user_in_context_from_request_plain_token():
    """ensure_user_in_context přijme token bez Bearer prefixu."""
    info = MagicMock()
    info.context = {"user": None, "request": None}
    request = MagicMock()
    request.headers = {"Authorization": "plain-token"}
    info.context["request"] = request
    result = ensure_user_in_context(info)
    assert result is not None
    assert result["id"] == "plain-token"


def test_ensure_user_in_context_user_without_id_uses_fallback():
    """Když user existuje ale nemá id, použije se __original_user."""
    info = MagicMock()
    info.context = {"user": {}, "__original_user": {"id": "original-789"}}
    result = ensure_user_in_context(info)
    assert result is not None
    assert result["id"] == "original-789"


# --- permissions ---


@pytest.mark.asyncio
async def test_user_has_role_with_roles_in_context():
    """user_has_role vrací True, když user má roli v context['user']['roles']."""
    from src.GraphTypeDefinitions.permissions import (
        user_has_role,
        ADMINISTRATOR_ROLE_ID,
    )
    from uuid import UUID
    info = MagicMock()
    info.context = {"loaders": MagicMock()}
    user = {
        "id": "76dac14f-7114-4bb2-882d-0d762eab6f4a",
        "roles": [{"roletype": {"id": str(ADMINISTRATOR_ROLE_ID)}}],
    }
    result = await user_has_role(user, "administrátor", info)
    assert result is True


@pytest.mark.asyncio
async def test_user_has_role_no_user():
    """user_has_role vrací False pro None user."""
    from src.GraphTypeDefinitions.permissions import user_has_role
    info = MagicMock()
    result = await user_has_role(None, "administrátor", info)
    assert result is False


@pytest.mark.asyncio
async def test_user_has_role_user_without_required_role():
    """user_has_role vrací False, když user nemá požadovanou roli v kontextu."""
    from src.GraphTypeDefinitions.permissions import user_has_role, VIEWER_ROLE_ID
    info = MagicMock()
    info.context = {"loaders": MagicMock()}
    user = {
        "id": "76dac14f-7114-4bb2-882d-0d762eab6f4a",
        "roles": [{"roletype": {"id": str(VIEWER_ROLE_ID)}}],
    }
    result = await user_has_role(user, "administrátor", info)
    assert result is False


@pytest.mark.asyncio
async def test_user_has_any_role_true():
    """user_has_any_role vrací True, pokud user má alespoň jednu z rolí."""
    from src.GraphTypeDefinitions.permissions import user_has_any_role, EDITOR_ROLE_ID
    info = MagicMock()
    info.context = {"loaders": MagicMock()}
    user = {
        "id": "76dac14f-7114-4bb2-882d-0d762eab6f4a",
        "roles": [{"roletype": {"id": str(EDITOR_ROLE_ID)}}],
    }
    result = await user_has_any_role(user, ["editor", "administrátor"], info)
    assert result is True


@pytest.mark.asyncio
async def test_user_has_any_role_false():
    """user_has_any_role vrací False, pokud user nemá žádnou z požadovaných rolí."""
    from unittest.mock import AsyncMock, patch
    from src.GraphTypeDefinitions.permissions import user_has_any_role, VIEWER_ROLE_ID
    info = MagicMock()
    info.context = {"loaders": MagicMock()}
    user = {
        "id": "76dac14f-7114-4bb2-882d-0d762eab6f4a",
        "roles": [{"roletype": {"id": str(VIEWER_ROLE_ID)}}],
    }
    # Bez patchu by get_user_roles_from_db mohl načíst role ze systemdata a test by byl flaky.
    with patch(
        "src.GraphTypeDefinitions.permissions.get_user_roles_from_db",
        new_callable=AsyncMock,
        return_value=set(),
    ):
        result = await user_has_any_role(user, ["administrátor", "editor"], info)
    assert result is False


def test_permissions_role_name_to_id():
    """ROLE_NAME_TO_ID obsahuje očekávané aliasy rolí."""
    from src.GraphTypeDefinitions.permissions import ROLE_NAME_TO_ID, ADMINISTRATOR_ROLE_ID
    assert ROLE_NAME_TO_ID.get("administrátor") == ADMINISTRATOR_ROLE_ID
    assert ROLE_NAME_TO_ID.get("admin") == ADMINISTRATOR_ROLE_ID


@pytest.mark.asyncio
async def test_get_user_roles_from_db_from_context():
    """get_user_roles_from_db vrací role z context['user']['roles']."""
    from src.GraphTypeDefinitions.permissions import get_user_roles_from_db, EDITOR_ROLE_ID
    from uuid import UUID
    info = MagicMock()
    user_id = UUID("76dac14f-7114-4bb2-882d-0d762eab6f4a")
    user = {
        "id": str(user_id),
        "roles": [{"roletype": {"id": str(EDITOR_ROLE_ID)}}],
    }
    info.context = {"loaders": MagicMock(), "user": user}
    role_ids = await get_user_roles_from_db(user_id, info)
    assert EDITOR_ROLE_ID in role_ids


# --- DBFeeder ---


def test_db_feeder_normalize_dataset_shapes():
    """_normalize_dataset_shapes přejmenuje *_evolution klíče na standardní názvy."""
    from src.DBFeeder import _normalize_dataset_shapes
    data = {
        "assets_evolution": [{"id": "a1"}],
        "asset_loans_evolution": [],
        "asset_inventory_records_evolution": [],
    }
    result = _normalize_dataset_shapes(data)
    assert "assets" in result
    assert result["assets"] == [{"id": "a1"}]
    assert "asset_loans" in result
    assert result["asset_loans"] == []


def test_db_feeder_get_demodata_returns_dict():
    """get_demodata vrací dict (systémová data)."""
    from pathlib import Path
    from src.DBFeeder import get_demodata, DEFAULT_DATA_PATH
    if not Path(DEFAULT_DATA_PATH).exists():
        pytest.skip("systemdata.json not found (optional for coverage)")
    data = get_demodata()
    assert isinstance(data, dict)


# --- Dataloaders ---


def test_create_loaders_returns_dict():
    """createLoaders vrací slovník loaderů."""
    from src.Dataloaders import createLoaders
    async def fake_session_factory():
        return None
    loaders = createLoaders(fake_session_factory)
    assert "AssetModel" in loaders
    assert "AssetLoanModel" in loaders
    assert "AssetInventoryRecordModel" in loaders


def test_create_loaders_context_has_loaders_and_session_maker():
    """createLoadersContext vrací kontext s loaders a session_maker na objektu."""
    from src.Dataloaders import createLoadersContext
    async def fake_session_factory():
        return None
    ctx = createLoadersContext(fake_session_factory)
    assert "loaders" in ctx
    assert hasattr(ctx["loaders"], "session_maker")
    assert ctx["loaders"].session_maker is fake_session_factory


def test_get_loaders_from_info():
    """getLoadersFromInfo vrací loaders z info.context."""
    from src.Dataloaders import getLoadersFromInfo
    fake_loaders = {"AssetModel": object()}
    info = MagicMock()
    info.context = {"loaders": fake_loaders}
    result = getLoadersFromInfo(info)
    assert result is fake_loaders
