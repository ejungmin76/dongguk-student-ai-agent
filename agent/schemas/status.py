from enum import StrEnum


class ResultStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    CLARIFICATION = "clarification"
    UNAVAILABLE = "unavailable"
