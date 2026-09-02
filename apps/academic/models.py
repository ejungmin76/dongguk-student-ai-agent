from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from .choices import (
    CourseStatus,
    DayOfWeek,
    EnrollmentStatus,
    GradeCode,
    OfferingStatus,
    Semester,
    StudentStatus,
)

class Major(models.Model):
    code = models.CharField(
        "전공 코드",
        max_length=20,
        unique=True,
    )
    name = models.CharField(
        "전공명",
        max_length=100,
    )
    college_name = models.CharField(
        "단과대학",
        max_length=100,
        blank=True,
    )
    is_active = models.BooleanField(
        "활성 상태",
        default=True,
    )
    created_at = models.DateTimeField(
        "생성일",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "수정일",
        auto_now=True,
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "전공"
        verbose_name_plural = "전공"

    def __str__(self):
        return f"{self.code} - {self.name}"


class AcademicTerm(models.Model):
    year = models.PositiveSmallIntegerField(
        "학년도",
        validators=[
            MinValueValidator(2000),
            MaxValueValidator(2100),
        ],
    )
    semester = models.CharField(
        "학기",
        max_length=10,
        choices=Semester.choices,
    )
    start_date = models.DateField(
        "시작일",
    )
    end_date = models.DateField(
        "종료일",
    )
    is_current = models.BooleanField(
        "현재 학기",
        default=False,
    )

    class Meta:
        ordering = ["-year", "semester"]
        verbose_name = "학기"
        verbose_name_plural = "학기"
        constraints = [
            models.UniqueConstraint(
                fields=["year", "semester"],
                name="unique_academic_term",
            ),
            models.UniqueConstraint(
                fields=["is_current"],
                condition=Q(is_current=True),
                name="unique_current_academic_term",
            ),
            models.CheckConstraint(
                condition=Q(year__gte=2000, year__lte=2100),
                name="academic_term_year_range",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="academic_term_valid_date_range",
            ),
        ]

    def __str__(self):
        return f"{self.year}학년도 {self.get_semester_display()}"

class Student(models.Model):
    student_number = models.CharField(
        "학번",
        max_length=20,
        unique=True,
    )
    display_name = models.CharField(
        "표시 이름",
        max_length=50,
    )
    admission_year = models.PositiveSmallIntegerField(
        "입학 연도",
        validators=[
            MinValueValidator(2000),
            MaxValueValidator(2100),
        ],
    )
    primary_major = models.ForeignKey(
        Major,
        verbose_name="주전공",
        on_delete=models.PROTECT,
        related_name="primary_students",
    )
    secondary_major = models.ForeignKey(
        Major,
        verbose_name="복수·부전공",
        on_delete=models.SET_NULL,
        related_name="secondary_students",
        null=True,
        blank=True,
    )
    current_semester = models.PositiveSmallIntegerField(
        "현재 학기",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(20),
        ],
    )
    status = models.CharField(
        "학적 상태",
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.ENROLLED,
    )
    created_at = models.DateTimeField(
        "생성일",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "수정일",
        auto_now=True,
    )

    class Meta:
        ordering = ["student_number"]
        verbose_name = "학생"
        verbose_name_plural = "학생"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    admission_year__gte=2000,
                    admission_year__lte=2100,
                ),
                name="student_admission_year_range",
            ),
            models.CheckConstraint(
                condition=Q(
                    current_semester__gte=1,
                    current_semester__lte=20,
                ),
                name="student_current_semester_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(secondary_major__isnull=True)
                    | ~Q(primary_major=F("secondary_major"))
                ),
                name="student_different_secondary_major",
            ),
        ]

    def __str__(self):
        return f"{self.student_number} - {self.display_name}"

class Course(models.Model):
    code = models.CharField(
        "과목 코드",
        max_length=30,
        unique=True,
    )
    name = models.CharField(
        "과목명",
        max_length=150,
    )
    default_credits = models.DecimalField(
        "기본 학점",
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(0.5),
            MaxValueValidator(10),
        ],
    )
    offering_major = models.ForeignKey(
        Major,
        verbose_name="개설 전공",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    status = models.CharField(
        "과목 상태",
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.ACTIVE,
    )
    description = models.TextField(
        "과목 설명",
        blank=True,
    )
    created_at = models.DateTimeField(
        "생성일",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "수정일",
        auto_now=True,
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "과목"
        verbose_name_plural = "과목"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    default_credits__gte=0.5,
                    default_credits__lte=10,
                ),
                name="course_default_credits_range",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

class CourseOffering(models.Model):
    course = models.ForeignKey(
        Course,
        verbose_name="과목",
        on_delete=models.PROTECT,
        related_name="offerings",
    )
    term = models.ForeignKey(
        AcademicTerm,
        verbose_name="개설 학기",
        on_delete=models.PROTECT,
        related_name="course_offerings",
    )
    section_number = models.CharField(
        "분반",
        max_length=10,
    )
    credits = models.DecimalField(
        "개설 학점",
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(0.5),
            MaxValueValidator(10),
        ],
    )
    professor_name = models.CharField(
        "담당 교수",
        max_length=100,
        blank=True,
    )
    capacity = models.PositiveIntegerField(
        "수강 정원",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    status = models.CharField(
        "개설 상태",
        max_length=20,
        choices=OfferingStatus.choices,
        default=OfferingStatus.SCHEDULED,
    )
    created_at = models.DateTimeField(
        "생성일",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "수정일",
        auto_now=True,
    )

    class Meta:
        ordering = ["-term__year", "course__code", "section_number"]
        verbose_name = "개설 강좌"
        verbose_name_plural = "개설 강좌"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "term", "section_number"],
                name="unique_course_term_section",
            ),
            models.CheckConstraint(
                condition=Q(credits__gte=0.5, credits__lte=10),
                name="course_offering_credits_range",
            ),
            models.CheckConstraint(
                condition=Q(capacity__isnull=True) | Q(capacity__gte=1),
                name="course_offering_capacity_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["term", "status"],
                name="offering_term_status_idx",
            ),
            models.Index(
                fields=["course", "term"],
                name="offering_course_term_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.term} / {self.course.code} "
            f"{self.course.name} / {self.section_number}분반"
        )

class CourseMeeting(models.Model):
    offering = models.ForeignKey(
        CourseOffering,
        verbose_name="개설 강좌",
        on_delete=models.CASCADE,
        related_name="meetings",
    )
    day_of_week = models.CharField(
        "요일",
        max_length=3,
        choices=DayOfWeek.choices,
    )
    start_time = models.TimeField(
        "시작 시간",
    )
    end_time = models.TimeField(
        "종료 시간",
    )
    classroom = models.CharField(
        "강의실",
        max_length=100,
        blank=True,
    )

    class Meta:
        ordering = ["day_of_week", "start_time"]
        verbose_name = "수업 시간"
        verbose_name_plural = "수업 시간"
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "day_of_week", "start_time"],
                name="unique_offering_meeting_time",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="course_meeting_valid_time_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["offering", "day_of_week"],
                name="meeting_offering_day_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.offering} / "
            f"{self.get_day_of_week_display()} "
            f"{self.start_time:%H:%M}-{self.end_time:%H:%M}"
        )

class Enrollment(models.Model):
    student = models.ForeignKey(
        Student,
        verbose_name="학생",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    offering = models.ForeignKey(
        CourseOffering,
        verbose_name="개설 강좌",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    status = models.CharField(
        "수강 상태",
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
    )
    enrolled_at = models.DateTimeField(
        "수강 신청일",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "수정일",
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-offering__term__year",
            "student__student_number",
            "offering__course__code",
        ]
        verbose_name = "수강 신청"
        verbose_name_plural = "수강 신청"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "offering"],
                name="unique_student_course_offering",
            ),
        ]
        indexes = [
            models.Index(
                fields=["student", "status"],
                name="enrollment_student_status_idx",
            ),
            models.Index(
                fields=["offering", "status"],
                name="enrollment_offering_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.student.student_number} / "
            f"{self.offering.course.code} / "
            f"{self.get_status_display()}"
        )

class AcademicRecord(models.Model):
    student = models.ForeignKey(
        Student,
        verbose_name="학생",
        on_delete=models.CASCADE,
        related_name="academic_records",
    )
    course = models.ForeignKey(
        Course,
        verbose_name="과목",
        on_delete=models.PROTECT,
        related_name="academic_records",
    )
    term = models.ForeignKey(
        AcademicTerm,
        verbose_name="수강 학기",
        on_delete=models.PROTECT,
        related_name="academic_records",
    )
    offering = models.ForeignKey(
        CourseOffering,
        verbose_name="개설 강좌",
        on_delete=models.SET_NULL,
        related_name="academic_records",
        null=True,
        blank=True,
    )

    # 과목 정보가 나중에 변경되어도 당시 성적표를 보존한다.
    course_code_snapshot = models.CharField(
        "당시 과목 코드",
        max_length=30,
    )
    course_name_snapshot = models.CharField(
        "당시 과목명",
        max_length=150,
    )
    credits_attempted = models.DecimalField(
        "신청 학점",
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10),
        ],
    )
    credits_earned = models.DecimalField(
        "취득 학점",
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10),
        ],
    )
    grade = models.CharField(
        "성적",
        max_length=2,
        choices=GradeCode.choices,
    )
    grade_points = models.DecimalField(
        "평점",
        max_digits=3,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(4.5),
        ],
        null=True,
        blank=True,
    )
    is_passed = models.BooleanField(
        "이수 통과",
    )
    attempt_number = models.PositiveSmallIntegerField(
        "수강 차수",
        default=1,
        validators=[MinValueValidator(1)],
    )
    created_at = models.DateTimeField(
        "생성일",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "수정일",
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-term__year",
            "student__student_number",
            "course__code",
            "attempt_number",
        ]
        verbose_name = "성적·이수 기록"
        verbose_name_plural = "성적·이수 기록"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "student",
                    "course",
                    "term",
                    "attempt_number",
                ],
                name="unique_student_course_term_attempt",
            ),
            models.CheckConstraint(
                condition=Q(
                    credits_attempted__gte=0,
                    credits_attempted__lte=10,
                ),
                name="academic_record_attempted_credits_range",
            ),
            models.CheckConstraint(
                condition=Q(
                    credits_earned__gte=0,
                    credits_earned__lte=10,
                ),
                name="academic_record_earned_credits_range",
            ),
            models.CheckConstraint(
                condition=Q(credits_earned__lte=F("credits_attempted")),
                name="academic_record_earned_lte_attempted",
            ),
            models.CheckConstraint(
                condition=(
                    Q(grade_points__isnull=True)
                    | Q(grade_points__gte=0, grade_points__lte=4.5)
                ),
                name="academic_record_grade_points_range",
            ),
            models.CheckConstraint(
                condition=Q(attempt_number__gte=1),
                name="academic_record_attempt_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["student", "term"],
                name="record_student_term_idx",
            ),
            models.Index(
                fields=["student", "course"],
                name="record_student_course_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.offering_id is None:
            return

        errors = {}

        if self.offering.course_id != self.course_id:
            errors["offering"] = "개설 강좌의 과목과 성적 과목이 다릅니다."

        if self.offering.term_id != self.term_id:
            errors["offering"] = "개설 강좌의 학기와 성적 학기가 다릅니다."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.student.student_number} / "
            f"{self.course_code_snapshot} / "
            f"{self.grade}"
        )