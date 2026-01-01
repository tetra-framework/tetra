import datetime
from django.contrib.messages.storage.base import Message
from django.db import models

from tetra.utils import to_json, from_json, NamedTemporaryUploadedFile


class MockModel(models.Model):
    class Meta:
        app_label = "main"


def test_basic_types():
    data = {
        "str": "hello",
        "int": 123,
        "float": 1.23,
        "bool": True,
        "none": None,
        "list": [1, 2, 3],
        "dict": {"a": 1},
    }
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert decoded["data"] == data


def test_datetime():
    dt = datetime.datetime(2023, 1, 1, 12, 30, 45, 123456)
    data = {"dt": dt}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert decoded["data"]["dt"].year == dt.year
    assert decoded["data"]["dt"].month == dt.month
    assert decoded["data"]["dt"].day == dt.day
    assert decoded["data"]["dt"].hour == dt.hour
    assert decoded["data"]["dt"].minute == dt.minute
    assert decoded["data"]["dt"].second == dt.second
    # TetraJSONEncoder truncates microseconds to 3 digits (milliseconds)
    assert decoded["data"]["dt"].microsecond == 123000


def test_date():
    d = datetime.date(2023, 1, 1)
    data = {"d": d}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    # date is decoded back as a datetime by datetime_parser.parse
    assert decoded["data"]["d"].date() == d


def test_time():
    t = datetime.time(12, 30, 45, 123456)
    data = {"t": t}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    # time is also decoded back as a datetime by datetime_parser.parse
    assert decoded["data"]["t"].time() == datetime.time(12, 30, 45, 123000)


def test_set():
    s = {1, 2, 3}
    data = {"s": s}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert decoded["data"]["s"] == s
    assert isinstance(decoded["data"]["s"], set)


def test_model(db):
    # We need a model instance. Since we might not have migrations for MockModel,
    # we can just mock the pk.
    model_inst = MockModel(pk=5)
    data = {"model": model_inst}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert decoded["data"]["model"] == 5


def test_message():
    msg = Message(level=20, message="Hello World", extra_tags="tag1 tag2")
    msg.uid = "test-uid"
    data = {"msg": msg}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert isinstance(decoded["data"]["msg"], Message)
    assert decoded["data"]["msg"].message == "Hello World"
    assert decoded["data"]["msg"].level == 20
    assert decoded["data"]["msg"].extra_tags == "tag1 tag2"
    assert decoded["data"]["msg"].uid == "test-uid"


def test_file():
    # Mock NamedTemporaryUploadedFile
    # It needs name, size, content_type, etc.
    f = NamedTemporaryUploadedFile(
        name="test.txt",
        content_type="text/plain",
        size=100,
        charset="utf-8",
        temp_path="/tmp/test.txt",
    )
    data = {"file": f}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert isinstance(decoded["data"]["file"], NamedTemporaryUploadedFile)
    assert decoded["data"]["file"].name == "test.txt"
    assert decoded["data"]["file"].size == 100
    assert decoded["data"]["file"].content_type == "text/plain"


def test_unknown_type_fallback():
    class Unknown:
        def __str__(self):
            return "unknown_str"

    data = {"u": Unknown()}
    json_str = to_json({"data": data})
    decoded = from_json(json_str)
    assert decoded["data"]["u"] == "unknown_str"


def test_none() -> None:
    assert to_json(None) == "{}"
