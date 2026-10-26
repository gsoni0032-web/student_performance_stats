"""Shared schema building blocks."""

from __future__ import annotations

import math
import re
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

T = TypeVar("T")

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class CamelModel(BaseModel):
    """Base model: camelCase on the wire, snake_case in Python, ORM objects accepted."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class Page(CamelModel, Generic[T]):
    """One page of results."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def of(cls, items: list[T], total: int, page: int, page_size: int) -> Page[T]:
        """Build a page, computing the page count."""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, math.ceil(total / page_size)),
        )


def clean_text(value: str) -> str:
    """Strip control characters and collapse whitespace so stored text is predictable."""
    return " ".join(_CONTROL_CHARS.sub("", value).split())


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
