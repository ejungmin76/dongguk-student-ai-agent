from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import Field, HttpUrl, PositiveInt

from .base import ContractModel


class SourceType(StrEnum):
    ACADEMIC_DATABASE = "academic_database"
    UNIVERSITY_DOCUMENT = "university_document"
    SERVICE_REGISTRY = "service_registry"


class SourceReference(ContractModel):
    """Traceable evidence without duplicating private result data."""

    source_id: Annotated[str, Field(min_length=1, max_length=100)]
    source_type: SourceType
    title: Annotated[str, Field(min_length=1, max_length=300)]
    url: HttpUrl | None = None
    page: PositiveInt | None = None
    effective_at: date | None = None
