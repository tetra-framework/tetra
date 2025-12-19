from typing import TypedDict, Any


class ComponentData(TypedDict):
    encrypted: str
    data: dict[str, Any]
    children: list["ComponentData"]
    args: list[str]
