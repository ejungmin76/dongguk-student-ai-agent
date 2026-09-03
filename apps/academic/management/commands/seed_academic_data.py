from datetime import date, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academic.choices import (
    CourseCategory, DayOfWeek, EnrollmentStatus, GradeCode,
    OfferingStatus, ProgramTrack, Semester, StudentStatus,
)
from apps.academic.models import (
    AcademicRecord, AcademicTerm, Course, CourseMeeting,
    CourseOffering, Enrollment, Major, Student,
)

# 학수번호와 전공/BSM 과목명은 2026 학업이수가이드 기준이다.
# MOCK-GEN 코드는 공식 학수번호를 오인하지 않도록 의도적으로 가상임을 표시한다.
CATALOG = (
    ("MOCK-GEN-01", "자아와명상1", 1, CourseCategory.GENERAL),
    ("MOCK-GEN-02", "커리어 디자인", 1, CourseCategory.GENERAL),
    ("PRI4001", "미적분학및연습1", 3, CourseCategory.BSM),
    ("CSC2001", "기초프로그래밍", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-03", "Global English 1", 3, CourseCategory.GENERAL),
    ("MOCK-GEN-04", "디지털 기술과 사회의 이해(자연/공학)", 3, CourseCategory.GENERAL),
    ("MOCK-GEN-05", "자아와명상2", 1, CourseCategory.GENERAL),
    ("MOCK-GEN-06", "불교와인간", 2, CourseCategory.GENERAL),
    ("PRI4023", "확률및통계학", 3, CourseCategory.BSM),
    ("CSC2002", "심화프로그래밍", 3, CourseCategory.MAJOR),
    ("CSC2004", "어드벤처디자인", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-07", "기업가정신과리더십", 2, CourseCategory.GENERAL),
    ("PRI4024", "공학선형대수학", 3, CourseCategory.BSM),
    ("PRI4027", "이산수학", 3, CourseCategory.BSM),
    ("CSC2007", "자료구조", 3, CourseCategory.MAJOR),
    ("CSC2003", "객체지향프로그래밍", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-08", "기술보고서작성및발표", 3, CourseCategory.GENERAL),
    ("MOCK-GEN-09", "자연과기술 명작세미나", 3, CourseCategory.GENERAL),
    ("MOCK-BSM-01", "일반물리학및실험1", 4, CourseCategory.BSM),
    ("MOCK-BSM-02", "미적분학및연습2", 3, CourseCategory.BSM),
    ("CSC2008", "알고리즘", 3, CourseCategory.MAJOR),
    ("CSC2011", "컴퓨터구성", 3, CourseCategory.MAJOR),
    ("CSC2005", "시스템소프트웨어", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-10", "프롬프트 기반 생성형 AI와 예술적 창작", 3, CourseCategory.GENERAL),
    ("CSC4001", "운영체제", 3, CourseCategory.MAJOR),
    ("CSC4009", "데이터베이스", 3, CourseCategory.MAJOR),
    ("CSC4012", "인공지능", 3, CourseCategory.MAJOR),
    ("CSC2006", "프로그래밍언어론", 3, CourseCategory.MAJOR),
    ("CSC4010", "소프트웨어공학", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-11", "빅데이터와 인공지능의 이해(자연/공학)", 3, CourseCategory.GENERAL),
    ("CSC4004", "공개SW프로젝트", 3, CourseCategory.MAJOR),
    ("CSC4013", "컴퓨터구조", 3, CourseCategory.MAJOR),
    ("CSC4011", "인간컴퓨터상호작용", 3, CourseCategory.MAJOR),
    ("CSC4021", "데이터통신입문", 3, CourseCategory.MAJOR),
    ("CSC4022", "머신러닝", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-12", "전쟁과 평화", 3, CourseCategory.GENERAL),
    ("CSC4018", "종합설계1", 3, CourseCategory.MAJOR),
    ("CSC4020", "데이터베이스설계", 3, CourseCategory.MAJOR),
    ("CSC4002", "컴퓨터그래픽스", 3, CourseCategory.MAJOR),
    ("CSC4014", "형식언어", 3, CourseCategory.MAJOR),
    ("CSC4024", "컴퓨터보안", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-13", "도심 재생과 지속가능 도시 실험", 3, CourseCategory.GENERAL),
    ("CSC4019", "종합설계2", 3, CourseCategory.MAJOR),
    ("CSC4015", "컴파일러", 3, CourseCategory.MAJOR),
    ("CSC4005", "임베디드시스템", 3, CourseCategory.MAJOR),
    ("CSC4031", "양자컴퓨팅", 3, CourseCategory.MAJOR),
    ("MOCK-GEN-14", "식탁의 정치학", 3, CourseCategory.GENERAL),
)

SCENARIOS = (
    ("MOCK-2026-001", "가상학생01", 1, StudentStatus.ENROLLED, ProgramTrack.GENERAL, None),
    ("MOCK-2026-002", "가상학생02", 3, StudentStatus.ENROLLED, ProgramTrack.GENERAL, None),
    ("MOCK-2026-003", "가상학생03", 4, StudentStatus.ENROLLED, ProgramTrack.ADVANCED, None),
    ("MOCK-2026-004", "가상학생04", 5, StudentStatus.ENROLLED, ProgramTrack.ADVANCED, None),
    ("MOCK-2026-005", "가상학생05", 6, StudentStatus.ENROLLED, ProgramTrack.GENERAL, "DS"),
    ("MOCK-2026-006", "가상학생06", 7, StudentStatus.ENROLLED, ProgramTrack.ADVANCED, None),
    ("MOCK-2026-007", "가상학생07", 3, StudentStatus.LEAVE, ProgramTrack.GENERAL, None),
    ("MOCK-2026-008", "가상학생08", 8, StudentStatus.ENROLLED, ProgramTrack.ADVANCED, None),
)

POINTS = {"A+": "4.5", "A0": "4.0", "B+": "3.5", "B0": "3.0", "C+": "2.5"}
GRADES = (GradeCode.A_ZERO, GradeCode.B_PLUS, GradeCode.A_PLUS, GradeCode.B_ZERO)


class Command(BaseCommand):
    help = "2026 학업이수가이드 기반의 개인정보 없는 Mock 학사 데이터를 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="기존 MOCK 전용 데이터를 지운 뒤 다시 생성")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_mock_data()
        majors = self._majors()
        terms = self._terms()
        courses = self._courses(majors)
        students = self._students(majors, terms)
        for number, _, semester_no, status, _, _ in SCENARIOS:
            student = students[number]
            completed_terms = semester_no - 1
            for term_index in range(completed_terms):
                for course_index in range(term_index * 6, min((term_index + 1) * 6, len(CATALOG))):
                    code = CATALOG[course_index][0]
                    offering = self._offering(courses[code], terms[term_index], course_index)
                    grade = GradeCode.C_PLUS if number == "MOCK-2026-006" and code == "CSC2002" else GRADES[course_index % 4]
                    self._record(student, offering, grade, number == "MOCK-2026-006" and code == "CSC2002")
            if number == "MOCK-2026-006":
                retake = self._offering(courses["CSC2002"], terms[2], 9)
                self._record(student, retake, GradeCode.A_ZERO, False, attempt=2)
            if status == StudentStatus.ENROLLED:
                for course_index in range(completed_terms * 6, min(semester_no * 6, len(CATALOG))):
                    offering = self._offering(courses[CATALOG[course_index][0]], terms[completed_terms], course_index)
                    Enrollment.objects.update_or_create(
                        student=student, offering=offering,
                        defaults={"status": EnrollmentStatus.ENROLLED},
                    )
        self.stdout.write(self.style.SUCCESS(
            f"Mock 생성 완료: 학생 {len(students)}명, 과목 {len(courses)}개"
        ))

    def _reset_mock_data(self):
        mock_students = Student.objects.filter(student_number__startswith="MOCK-")
        AcademicRecord.objects.filter(student__in=mock_students).delete()
        Enrollment.objects.filter(student__in=mock_students).delete()
        mock_students.delete()
        mock_offerings = CourseOffering.objects.filter(professor_name="가상교수")
        CourseMeeting.objects.filter(offering__in=mock_offerings).delete()
        mock_offerings.delete()
        Course.objects.filter(description__startswith="[MOCK-SEED]").delete()

    def _majors(self):
        result = {}
        for code, name, college in (("CAI", "컴퓨터·AI학부", "첨단융합대학"), ("DS", "데이터사이언스전공", "첨단융합대학"), ("DGC", "다르마칼리지", "다르마칼리지")):
            result[code] = Major.objects.update_or_create(code=code, defaults={"name": name, "college_name": college})[0]
        return result

    def _terms(self):
        result = []
        for index in range(8):
            year, semester = 2026 + index // 2, Semester.FIRST if index % 2 == 0 else Semester.SECOND
            month = 3 if semester == Semester.FIRST else 9
            result.append(AcademicTerm.objects.update_or_create(
                year=year, semester=semester,
                defaults={"start_date": date(year, month, 2), "end_date": date(year, 6 if month == 3 else 12, 21)},
            )[0])
        return result

    def _courses(self, majors):
        result = {}
        for code, name, credits, category in CATALOG:
            owner = majors["DGC"] if category == CourseCategory.GENERAL else majors["CAI"]
            result[code] = Course.objects.update_or_create(
                code=code,
                defaults={"name": name, "default_credits": Decimal(credits), "offering_major": owner,
                          "category": category, "is_english": False,
                          "description": "[MOCK-SEED] 2026 학업이수가이드 기반 시나리오 과목"},
            )[0]
        return result

    def _students(self, majors, terms):
        result = {}
        for number, name, semester_no, status, track, secondary in SCENARIOS:
            result[number] = Student.objects.update_or_create(
                student_number=number,
                defaults={"display_name": name, "admission_year": 2026, "curriculum_year": 2026,
                          "primary_major": majors["CAI"], "secondary_major": majors.get(secondary),
                          "current_semester": semester_no, "program_track": track,
                          "reference_term": terms[semester_no - 1], "status": status},
            )[0]
        return result

    def _offering(self, course, term, index):
        offering = CourseOffering.objects.update_or_create(
            course=course, term=term, section_number="01",
            defaults={"credits": course.default_credits, "professor_name": "가상교수",
                      "capacity": 40, "status": OfferingStatus.OPEN},
        )[0]
        start_hour = 9 + index % 6
        CourseMeeting.objects.update_or_create(
            offering=offering, day_of_week=(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY)[index % 4],
            start_time=time(start_hour, 0), defaults={"end_time": time(start_hour + 1, 15), "classroom": "가상강의실"},
        )
        return offering

    def _record(self, student, offering, grade, replaced, attempt=1):
        course = offering.course
        AcademicRecord.objects.update_or_create(
            student=student, course=course, term=offering.term, attempt_number=attempt,
            defaults={"offering": offering, "course_code_snapshot": course.code,
                      "course_name_snapshot": course.name, "credits_attempted": course.default_credits,
                      "credits_earned": course.default_credits, "grade": grade,
                      "grade_points": Decimal(POINTS[grade]), "is_passed": True,
                      "is_replaced_by_retaking": replaced},
        )
