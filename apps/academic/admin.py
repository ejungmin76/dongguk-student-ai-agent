from django.contrib import admin

from .models import (
    AcademicRecord,
    AcademicTerm,
    Course,
    CourseMeeting,
    CourseOffering,
    Enrollment,
    Major,
    Student,
)


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "college_name",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "college_name",
    )
    list_filter = ("is_active",)
    ordering = ("code",)


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "semester",
        "start_date",
        "end_date",
        "is_current",
    )
    search_fields = (
        "=year",
        "semester",
    )
    list_filter = (
        "year",
        "semester",
        "is_current",
    )
    ordering = (
        "-year",
        "semester",
    )

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_number",
        "display_name",
        "admission_year",
        "primary_major",
        "secondary_major",
        "current_semester",
        "status",
    )
    search_fields = (
        "student_number",
        "display_name",
        "primary_major__code",
        "primary_major__name",
    )
    list_filter = (
        "status",
        "admission_year",
        "primary_major",
    )
    autocomplete_fields = (
        "primary_major",
        "secondary_major",
    )
    list_select_related = (
        "primary_major",
        "secondary_major",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("student_number",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "default_credits",
        "offering_major",
        "status",
    )
    search_fields = (
        "code",
        "name",
        "offering_major__code",
        "offering_major__name",
    )
    list_filter = (
        "status",
        "offering_major",
    )
    autocomplete_fields = ("offering_major",)
    list_select_related = ("offering_major",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("code",)


class CourseMeetingInline(admin.TabularInline):
    model = CourseMeeting
    extra = 1
    fields = (
        "day_of_week",
        "start_time",
        "end_time",
        "classroom",
    )


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "term",
        "section_number",
        "credits",
        "professor_name",
        "capacity",
        "status",
    )
    search_fields = (
        "course__code",
        "course__name",
        "professor_name",
        "section_number",
    )
    list_filter = (
        "term__year",
        "term__semester",
        "status",
        "course__offering_major",
    )
    autocomplete_fields = (
        "course",
        "term",
    )
    list_select_related = (
        "course",
        "term",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    inlines = (CourseMeetingInline,)


@admin.register(CourseMeeting)
class CourseMeetingAdmin(admin.ModelAdmin):
    list_display = (
        "offering",
        "day_of_week",
        "start_time",
        "end_time",
        "classroom",
    )
    search_fields = (
        "offering__course__code",
        "offering__course__name",
        "classroom",
    )
    list_filter = ("day_of_week",)
    autocomplete_fields = ("offering",)
    list_select_related = (
        "offering",
        "offering__course",
        "offering__term",
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "offering",
        "status",
        "enrolled_at",
    )
    search_fields = (
        "student__student_number",
        "student__display_name",
        "offering__course__code",
        "offering__course__name",
    )
    list_filter = (
        "status",
        "offering__term__year",
        "offering__term__semester",
    )
    autocomplete_fields = (
        "student",
        "offering",
    )
    list_select_related = (
        "student",
        "offering",
        "offering__course",
        "offering__term",
    )
    readonly_fields = (
        "enrolled_at",
        "updated_at",
    )


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course_code_snapshot",
        "course_name_snapshot",
        "term",
        "grade",
        "grade_points",
        "credits_earned",
        "is_passed",
        "attempt_number",
    )
    search_fields = (
        "student__student_number",
        "student__display_name",
        "course__code",
        "course__name",
        "course_code_snapshot",
        "course_name_snapshot",
    )
    list_filter = (
        "term__year",
        "term__semester",
        "grade",
        "is_passed",
        "course__offering_major",
    )
    autocomplete_fields = (
        "student",
        "course",
        "term",
        "offering",
    )
    list_select_related = (
        "student",
        "course",
        "term",
        "offering",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )