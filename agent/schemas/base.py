from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Strict base class for data exchanged across application boundaries."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )
