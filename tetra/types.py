from typing import TypedDict, Any


class ComponentData(TypedDict):
    state: str
    data: dict[str, Any]
    children: list["ComponentData"]
    args: [str]
