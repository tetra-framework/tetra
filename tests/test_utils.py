import json
import zoneinfo
from datetime import datetime, timedelta

import pytest

from tests.main.models import SimpleModel, AwareDateTimeModel
from tetra.utils import (
    TetraJSONDecoder,
    TetraJSONEncoder,
    isclassmethod,
    underscore_to_pascal_case,
    camel_case_to_underscore,
    remove_surrounding_quotes,
)


@pytest.fixture
def simple_model_instance():
    # Create an instance of SimpleModel
    instance = SimpleModel.objects.create(name="Test Model")
    return instance


@pytest.mark.django_db
def test_TetraJSONEn_Decoder_with_model(simple_model_instance):

    # Serialize the Model instance using the TetraJSONEncoder
    serialized_instance: str = json.dumps(simple_model_instance, cls=TetraJSONEncoder)

    pk = json.loads(serialized_instance)
    assert pk == simple_model_instance.pk


def test_encoding_decoding_with_aware_datetime():
    # Create a model instance with an aware datetime field

    tz = zoneinfo.ZoneInfo("Europe/Vienna")
    created_at: datetime = datetime.now(tz=tz)
    # model = AwareDateTimeModel.objects.create(
    #     name="Aware DateTime Model",
    #     created_at=created_at,
    # )
    # Serialize the Model instance using the TetraJSONEncoder
    serialized_instance = json.dumps(created_at, cls=TetraJSONEncoder)

    # Parse the serialized instance back into a Python object - it should be a
    # datetime again
    deserialized_datetime = json.loads(serialized_instance, cls=TetraJSONDecoder)

    # Assert that the parsed instance is of the correct type
    assert isinstance(deserialized_datetime, datetime)

    # Assert that the parsed instance has the correct datetime format (except the
    # microseconds)
    assert deserialized_datetime.replace(microsecond=0) == created_at.replace(
        microsecond=0
    )
    assert len(str(created_at)) > 26  # ISO 8601 format with timezone


def _timedelta_to_offset_string(td: timedelta) -> str:
    """
    Helper function that converts a timedelta to a timezone offset string.

    Returns:
        str: A string representation of the offset in the format "+HH:MM" or "-HH:MM".
    """
    total_seconds = int(td.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def test_timezone_aware_datetime_encoding():
    # Create a model instance with an aware datetime field

    tz = zoneinfo.ZoneInfo("Europe/Berlin")
    now = datetime.now(tz=tz)

    # use only first 3 digits (of 6) of microsecond. Tetra cuts the last 3 digits,
    # resulting in a wrong comparison.
    now = now.replace(microsecond=234000)

    # Serialize the model instance using the TetraJSONEncoder
    serialized_instance = json.dumps(now, cls=TetraJSONEncoder)

    # Parse the serialized instance back into a Python object using the normal Python
    # decoder - it should be a dict then.
    parsed_instance = json.loads(serialized_instance)

    # Assert that the parsed instance is of the correct type and has the correct
    # attributes
    assert isinstance(parsed_instance, dict)
    assert "__type" in parsed_instance
    assert parsed_instance["__type"] == "datetime"
    assert "value" in parsed_instance
    assert isinstance(parsed_instance["value"], str)

    # Assert that the parsed instance has the correct datetime format
    value = parsed_instance["value"]
    # make sure the timezone offset is correct
    assert value.endswith(_timedelta_to_offset_string(tz.utcoffset(now)))

    # make sure the parsed instance has the correct datetime value as the original
    assert datetime.fromisoformat(value) == now


class MockClass:
    @classmethod
    def class_method(cls):
        pass

    def noclass_method(self):
        pass


def test_isclassmethod():
    test_class = MockClass()
    assert isclassmethod(test_class.class_method) is True
    assert isclassmethod(test_class.noclass_method) is False

    assert isclassmethod(MockClass.class_method) is True
    assert isclassmethod(MockClass.noclass_method) is False


def test_camel_case_to_underscore():
    # normal camel case to underscore conversion
    assert camel_case_to_underscore("camelCase") == "camel_case"
    assert camel_case_to_underscore("PascalCase") == "pascal_case"
    # single word
    assert camel_case_to_underscore("Camel") == "camel"
    # multiple words
    assert (
        camel_case_to_underscore("CamelCaseToUnderscore") == "camel_case_to_underscore"
    )
    # multiple uppercase letters
    assert camel_case_to_underscore("ABC") == "abc"
    # input is already lower case
    assert camel_case_to_underscore("already_lower") == "already_lower"
    # empty string
    assert camel_case_to_underscore("") == ""
    # input is just a single capital letter
    assert camel_case_to_underscore("A") == "a"
    # digits
    assert camel_case_to_underscore("CamelCase1") == "camel_case1"


def test_underscore_to_pascal_case():
    # normal snake_case to PascalCase conversion
    assert underscore_to_pascal_case("my_example_string") == "MyExampleString"
    # single lowercase word
    assert underscore_to_pascal_case("example") == "Example"
    # leading and trailing underscores
    assert underscore_to_pascal_case("_leading_underscore") == "LeadingUnderscore"
    assert underscore_to_pascal_case("trailing_underscore_") == "TrailingUnderscore"
    # multiple underscores
    assert underscore_to_pascal_case("multiple___underscores") == "MultipleUnderscores"
    # empty string
    assert underscore_to_pascal_case("") == ""
    # numbers
    assert underscore_to_pascal_case("example_with_123") == "ExampleWith123"
    # already PascalCase
    assert underscore_to_pascal_case("PascalCase") == "PascalCase"


def test_remove_surrounding_quotes_double_quotes():
    """Should remove surrounding double quotes from a string"""
    test_string = '"test string"'
    result = remove_surrounding_quotes(test_string)
    assert result == "test string"


def test_remove_surrounding_quotes_single_quotes():
    """Should remove surrounding single quotes from a string"""
    test_string = "'test string'"
    result = remove_surrounding_quotes(test_string)
    assert result == "test string"


def test_remove_surrounding_quotes_no_quotes():
    """Should not modify a string without surrounding quotes"""
    test_string = "test string"
    result = remove_surrounding_quotes(test_string)
    assert result == "test string"


def test_remove_surrounding_quotes_single_character():
    """Should handle a string with just one character (a quote)"""
    test_string = '"'
    result = remove_surrounding_quotes(test_string)
    # A single quote character should remain unchanged
    assert result == '"'


def test_remove_surrounding_quotes_first_character_quote():
    """Should handle a string where only the first character is a quote"""
    test_string = '"test string'
    result = remove_surrounding_quotes(test_string)
    # String should remain unchanged since quotes aren't surrounding
    assert result == '"test string'


def test_remove_surrounding_quotes_last_character_quote():
    """Should handle a string where only the last character is a quote"""
    test_string = "test string'"
    result = remove_surrounding_quotes(test_string)
    # String should remain unchanged since quotes aren't surrounding
    assert result == "test string'"


def test_remove_surrounding_quotes_different_quote_types():
    """Should handle a string with different quote types at beginning and end"""
    test_string = "\"test string'"
    result = remove_surrounding_quotes(test_string)
    # String should remain unchanged since quotes don't match
    assert result == "\"test string'"


def test_remove_surrounding_quotes_empty_string():
    """Should handle an empty string without raising an IndexError"""
    test_string = ""
    result = remove_surrounding_quotes(test_string)
    # Empty string should remain unchanged
    assert result == ""


def test_remove_surrounding_quotes_whitespace_string():
    """Should handle an empty string without raising an IndexError"""
    test_string = " "
    result = remove_surrounding_quotes(test_string)
    # Empty whitespace string should remain unchanged
    assert result == " "


def test_remove_surrounding_quotes_quotes_in_middle():
    """Should properly handle strings that have quotes in the middle but not at the edges"""
    test_string = 'text "quoted" text'
    result = remove_surrounding_quotes(test_string)
    # String should remain unchanged since quotes are only in the middle
    assert result == 'text "quoted" text'


def test_remove_surrounding_quotes_multiple_quotes():
    """Should handle a string that consists of multiple quotes"""
    test_string = '"""triple quoted"""'
    result = remove_surrounding_quotes(test_string)
    # Only the outermost quotes should be removed
    assert result == "triple quoted"
