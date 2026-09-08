from pydantic import Field, model_validator

from agent.schemas.base import ContractModel


class StudentProfileToolInput(ContractModel):
    target_student_number: str | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode="after")
    def reject_blank_target(self):
        if self.target_student_number == "":
            raise ValueError("target_student_number cannot be blank")
        return self


class StudentProfileToolData(ContractModel):
    student_number: str
    display_name: str
    admission_year: int
    current_semester: int
    status: str
    program_track: str
    primary_major_name: str
    secondary_major_name: str | None = None
