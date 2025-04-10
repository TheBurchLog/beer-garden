# -*- coding: utf-8 -*-
from beer_garden.db.mongo.fields import DummyField


class TestDummyField(object):
    @pytest.mark.benchmark
    def test_to_python(self):
        field = DummyField()
        assert field.to_python("value") == "value"

    @pytest.mark.benchmark
    def test_to_mongo(self):
        field = DummyField()
        assert field.to_mongo("value") is None
