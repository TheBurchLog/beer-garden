# -*- coding: utf-8 -*-
import pytest
from brewtils.models import Operation
from mock import Mock

import beer_garden.garden
import beer_garden.router
from beer_garden.errors import UnknownGardenException
from beer_garden.router import _determine_target

pytestmark = pytest.mark.benchmark

@pytest.fixture
def op():
    return Operation(source_garden_name="parent")


class TestDetermineTarget:
    @pytest.mark.benchmark
    def test_neither(self, monkeypatch, op):
        monkeypatch.setattr(
            beer_garden.router, "_target_from_type", Mock(return_value=None)
        )
        with pytest.raises(UnknownGardenException):
            _determine_target(op)

    @pytest.mark.benchmark
    def test_target_from_op(self, monkeypatch, op):
        monkeypatch.setattr(
            beer_garden.router, "_target_from_type", Mock(return_value=None)
        )
        op.target_garden_name = "parent"

        assert _determine_target(op) == "parent"

    @pytest.mark.benchmark
    def test_target_from_type(self, monkeypatch, op):
        monkeypatch.setattr(
            beer_garden.router, "_target_from_type", Mock(return_value="parent")
        )

        assert _determine_target(op) == "parent"

    @pytest.mark.benchmark
    def test_same(self, monkeypatch, op):
        monkeypatch.setattr(
            beer_garden.router, "_target_from_type", Mock(return_value="child")
        )
        op.target_garden_name = "child"

        assert _determine_target(op) == "child"

    @pytest.mark.benchmark
    def test_mismatch(self, monkeypatch, op):
        monkeypatch.setattr(
            beer_garden.router, "_target_from_type", Mock(return_value="child")
        )
        op.target_garden_name = "parent"

        assert _determine_target(op) == "child"
