from unittest.mock import Mock

import pytest

from app.ai.registry import ModelRegistry


def test_promotion_deactivates_previous_model() -> None:
    repository = Mock()
    repository.session = Mock()
    target = Mock(id=2, dataset_id=10, status="CANDIDATE", promoted_at=None)
    current = Mock(id=1, dataset_id=10, status="ACTIVE")
    repository.get_model_for_update.return_value = target
    repository.get_active_model_for_update.return_value = current

    result = ModelRegistry(repository).promote(2)

    assert result is target
    assert target.status == "ACTIVE"
    assert target.promoted_at is not None
    assert current.status == "INACTIVE"
    assert current.deactivated_at is not None
    repository.session.commit.assert_called_once_with()


def test_missing_model_rolls_back() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.get_model_for_update.return_value = None

    with pytest.raises(ValueError, match="não encontrado"):
        ModelRegistry(repository).promote(999)

    repository.session.rollback.assert_called_once_with()
