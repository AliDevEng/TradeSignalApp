"""Unit tests for :class:`PairController` — the pair lookup read service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.pair_controller import PairController
from app.schemas.pair import PairResponse

from tests._factories import make_pair


def _controller(pairs: AsyncMock | None = None):
    pairs = pairs or AsyncMock()
    return PairController(pairs=pairs), pairs


async def test_list_pairs_active_only_by_default():
    ctrl, pairs = _controller()
    pairs.list_active.return_value = [make_pair(symbol="EURUSD"), make_pair(symbol="GBPUSD")]

    result = await ctrl.list_pairs()

    assert len(result) == 2
    assert all(isinstance(p, PairResponse) for p in result)
    pairs.list_active.assert_awaited_once()
    pairs.list_all.assert_not_awaited()


async def test_list_pairs_include_inactive_uses_list_all():
    ctrl, pairs = _controller()
    pairs.list_all.return_value = [make_pair(is_active=False)]

    result = await ctrl.list_pairs(include_inactive=True)

    assert result[0].is_active is False
    pairs.list_all.assert_awaited_once()
    pairs.list_active.assert_not_awaited()


async def test_get_pair_returns_mapped_response():
    ctrl, pairs = _controller()
    pairs.get_by_symbol.return_value = make_pair(symbol="XAUUSD", base_currency="XAU")

    result = await ctrl.get_pair("XAUUSD")

    assert isinstance(result, PairResponse)
    assert result.symbol == "XAUUSD"
    assert result.base_currency == "XAU"


async def test_get_pair_missing_raises_not_found():
    ctrl, pairs = _controller()
    pairs.get_by_symbol.return_value = None

    with pytest.raises(ResourceNotFoundError) as exc:
        await ctrl.get_pair("NOPE")
    assert exc.value.resource == "pair"
    assert exc.value.identifier == "NOPE"
