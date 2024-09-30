import json
from datetime import datetime

import pytest
from django.utils import timezone

from tests.main.models import SimpleModel, AwareDateTimeModel
from tetra.utils import (
    TetraJSONDecoder,
    TetraJSONEncoder,
    isclassmethod,
    underscore_to_pascal_case,
    camel_case_to_underscore,
)


@pytest.fixture
def simple_model_instance():
    # Create an instance of SimpleModel
    instance = SimpleModel(name="Test Model")
    instance.save()
    return instance


@pytest.mark.django_db
def test_TetraJSONEncoder_with_model(simple_model_instance):

    # Serialize the Model instance using the TetraJSONEncoder
    serialized_instance: str = json.dumps(simple_model_instance, cls=TetraJSONEncoder)

    # Parse the serialized instance back into a Python object using the normal Python
    # decoder - it should be a dict then.
    parsed_instance = json.loads(serialized_instance)
    assert "__type" in parsed_instance
    assert parsed_instance["__type"] == "model.main.SimpleModel"
    assert "value" in parsed_instance
    assert isinstance(parsed_instance["value"], int)


@pytest.mark.django_db
def test_TetraJSONDecoder_with_model(simple_model_instance):
    # Serialize the Model instance using the TetraJSONEncoder
    serialized_instance: str = json.dumps(simple_model_instance, cls=TetraJSONEncoder)
    # Parse the serialized instance back into a Python object - it should be a Model
    # again.
    parsed_instance = json.loads(serialized_instance, cls=TetraJSONDecoder)

    # Assert that the parsed instance is of the correct type and has the correct
    # attributes
    assert isinstance(parsed_instance, SimpleModel)
    assert parsed_instance.name == "Test Model"


@pytest.mark.django_db
def test_model_encoding_with_aware_datetime():
    # Create a model instance with an aware datetime field

    now = timezone.now()

    # Serialize the model instance using the TetraJSONEncoder
    serialized_instance = json.dumps(now, cls=TetraJSONEncoder)

    # Parse the serialized instance back into a Python object using the normal Python
    # decoder - it should be a dict then.
    parsed_instance = json.loads(serialized_instance)

    # Assert that the parsed instance is of the correct type and has the correct
    # attributes
    assert isinstance(parsed_instance, dict)
    assert "__type" in parsed_instance
    assert parsed_instance["__type"] == "model.main.AwareDateTimeModel"
    assert "value" in parsed_instance
    assert isinstance(parsed_instance["value"], int)  # This should be the primary key

    # Assert that the parsed instance has the correct attributes
    assert "name" in parsed_instance
    assert isinstance(parsed_instance["name"], str)
    assert parsed_instance["name"] == "Aware DateTime Model"

    # Assert that the parsed instance has the correct datetime format
    assert "created_at" in parsed_instance
    assert isinstance(parsed_instance["created_at"], str)
    assert len(parsed_instance["created_at"]) > 26  # ISO 8601 format with timezone
    parsed_instance = json.loads(serialized_instance)


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
