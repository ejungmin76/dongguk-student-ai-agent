from django.db import models


class Semester(models.TextChoices):
    FIRST = "first", "1학기"
    SUMMER = "summer", "여름학기"
    SECOND = "second", "2학기"
    WINTER = "winter", "겨울학기"


class StudentStatus(models.TextChoices):
    ENROLLED = "enrolled", "재학"
    LEAVE = "leave", "휴학"
    GRADUATED = "graduated", "졸업"


class ProgramTrack(models.TextChoices):
    GENERAL = "general", "일반과정"
    ADVANCED = "advanced", "심화과정"


class CourseStatus(models.TextChoices):
    ACTIVE = "active", "활성"
    INACTIVE = "inactive", "비활성"


class CourseCategory(models.TextChoices):
    MAJOR = "major", "전공"
    BSM = "bsm", "BSM"
    GENERAL = "general", "교양"


class EnrollmentStatus(models.TextChoices):
    ENROLLED = "enrolled", "수강 중"
    DROPPED = "dropped", "수강 취소"
    COMPLETED = "completed", "이수 완료"

class OfferingStatus(models.TextChoices):
    SCHEDULED = "scheduled", "개설 예정"
    OPEN = "open", "수강 가능"
    CLOSED = "closed", "마감"
    CANCELLED = "cancelled", "폐강"


class DayOfWeek(models.TextChoices):
    MONDAY = "mon", "월요일"
    TUESDAY = "tue", "화요일"
    WEDNESDAY = "wed", "수요일"
    THURSDAY = "thu", "목요일"
    FRIDAY = "fri", "금요일"
    SATURDAY = "sat", "토요일"
    SUNDAY = "sun", "일요일"


class GradeCode(models.TextChoices):
    A_PLUS = "A+", "A+"
    A_ZERO = "A0", "A0"
    B_PLUS = "B+", "B+"
    B_ZERO = "B0", "B0"
    C_PLUS = "C+", "C+"
    C_ZERO = "C0", "C0"
    D_PLUS = "D+", "D+"
    D_ZERO = "D0", "D0"
    F = "F", "F"
    PASS = "P", "Pass"
    NON_PASS = "NP", "Non-Pass"
    WITHDRAWN = "W", "수강 철회"
    INCOMPLETE = "I", "미완료"
