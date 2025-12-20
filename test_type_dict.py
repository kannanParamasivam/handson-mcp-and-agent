from typing import TypedDict


class Point(TypedDict):
    x: int
    y: int


p: Point = {"x": 10, "y": 20}  # type-checker OK

p["z"] = 30  # type-checker error: extra key not defined in TypedDict
print(type(p))
print(p)
