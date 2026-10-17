"""
Workflow and operational lifecycle tests for Phase 5.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from academics.models import College, Department, Program, Scheme, Semester, Course, Batch, StudentProfile, FacultyProfile
from academics.services import AcademicWorkflowService
from enrollment.models import (
    CourseOffering,
    StudentCourseEnrollment,
    AttendanceSession,
    AttendanceRecord,
    AssessmentComponent,
    StudentMark,
)


class AcademicWorkflowServiceTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.college = College.objects.create(code="RVCE", name="R.V. College of Engineering")
        self.dept = Department.objects.create(college=self.college, code="CSE", name="Computer Science")
        self.prog = Program.objects.create(
            department=self.dept, code="BTECH-CS", name="B.Tech Computer Science", duration_years=4, total_semesters=8
        )
        self.scheme = Scheme.objects.create(
            program=self.prog, code="SCH2024", name="2024 Scheme", effective_year=2024, total_credits_required=Decimal("160.00")
        )
        self.sem1 = Semester.objects.create(scheme=self.scheme, semester_number=1, semester_type="ODD")
        self.course1 = Course.objects.create(
            semester=self.sem1, code="CS101", title="Intro to Computing", credits=Decimal("4.00")
        )
        self.course2 = Course.objects.create(
            semester=self.sem1, code="MAT101", title="Calculus", credits=Decimal("4.00")
        )

        self.sem2 = Semester.objects.create(scheme=self.scheme, semester_number=2, semester_type="EVEN")
        self.course3 = Course.objects.create(
            semester=self.sem2, code="CS102", title="OOP with Java", credits=Decimal("4.00")
        )

        self.batch = Batch.objects.create(
            program=self.prog, scheme=self.scheme, name="2024 Batch A", admission_year=2024, graduation_year=2028, current_semester=1
        )

        # Users
        self.dept_user = User.objects.create_user("dept_admin", "dept@rvce.edu.in", "pass123", role=User.Role.DEPT_ADMIN, assigned_department=self.dept)
        self.faculty_user = User.objects.create_user("fac_smith", "fac@rvce.edu.in", "pass123", role=User.Role.FACULTY)
        self.faculty_prof = FacultyProfile.objects.create(
            user=self.faculty_user, department=self.dept, employee_id="EMP-101", designation="Associate Professor"
        )

        # Active Students
        self.students = []
        for i in range(5):
            u = User.objects.create_user(f"stud_{i}", f"stud_{i}@rvce.edu.in", "pass123", role=User.Role.STUDENT)
            sp = StudentProfile.objects.create(
                user=u, batch=self.batch, register_number=f"1RV24CS{100+i}", roll_number=f"CS-{i+1}"
            )
            self.students.append(sp)

    def test_scheme_cloning_workflow(self):
        """WP 5.1: Scheme cloning duplicates all semesters and courses under new code."""
        cloned = AcademicWorkflowService.clone_scheme(
            source_scheme_id=self.scheme.id,
            new_code="SCH2028",
            new_name="2028 NextGen Scheme",
            effective_year=2028,
        )

        self.assertEqual(cloned.code, "SCH2028")
        self.assertEqual(cloned.effective_year, 2028)
        self.assertEqual(cloned.semesters.count(), 2)

        cloned_sem1 = cloned.semesters.get(semester_number=1)
        self.assertEqual(cloned_sem1.courses.count(), 2)
        self.assertTrue(cloned_sem1.courses.filter(code="CS101").exists())
        self.assertTrue(cloned_sem1.courses.filter(code="MAT101").exists())

    def test_batch_semester_promotion(self):
        """WP 5.2: Batch promotion increments semester and graduates at cap."""
        # 1. Promote from sem 1 to sem 2
        result = AcademicWorkflowService.promote_batch(self.batch.id)
        self.assertEqual(result["status"], "PROMOTED")
        self.assertEqual(result["new_semester"], 2)

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.current_semester, 2)
        self.assertFalse(self.batch.is_graduated)

        # 2. Set to final semester and promote -> graduates
        self.batch.current_semester = 8
        self.batch.save()

        grad_result = AcademicWorkflowService.promote_batch(self.batch.id)
        self.assertEqual(grad_result["status"], "GRADUATED")

        self.batch.refresh_from_db()
        self.assertTrue(self.batch.is_graduated)

        # Verify students transitioned to GRADUATED
        for sp in self.students:
            sp.refresh_from_db()
            self.assertEqual(sp.status, StudentProfile.StudentStatus.GRADUATED)

    def test_automated_offering_generation_and_bulk_enrollment(self):
        """WP 5.3 & 5.4: Automated offering generation and bulk enrollment."""
        # Generate offerings for Semester 1 (2 courses)
        offerings = AcademicWorkflowService.generate_course_offerings_for_batch(
            batch_id=self.batch.id,
            academic_year="2024-2025",
            term="ODD",
            section="A",
            default_faculty_map={"CS101": self.faculty_prof},
        )

        self.assertEqual(len(offerings), 2)
        cs101_offering = CourseOffering.objects.get(course__code="CS101", batch=self.batch)
        self.assertEqual(cs101_offering.faculty, self.faculty_prof)

        # Bulk enroll all 5 students into the 2 courses -> 10 enrollments
        enrolled_count = AcademicWorkflowService.bulk_enroll_batch_students(
            batch_id=self.batch.id,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )

        self.assertEqual(enrolled_count, 10)
        self.assertEqual(StudentCourseEnrollment.objects.filter(course_offering=cs101_offering).count(), 5)

        # Subsequent bulk enrollment call should be idempotent (0 new created)
        second_call_count = AcademicWorkflowService.bulk_enroll_batch_students(
            batch_id=self.batch.id,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )
        self.assertEqual(second_call_count, 0)

    def test_export_roster_csv_view(self):
        """Faculty roster CSV export produces valid CSV download with student records."""
        # Create offering and enrollments
        offering = CourseOffering.objects.create(
            course=self.course1,
            batch=self.batch,
            faculty=self.faculty_prof,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )
        for sp in self.students:
            StudentCourseEnrollment.objects.create(student=sp, course_offering=offering)

        # Login as assigned faculty
        self.client.login(username="fac_smith", password="pass123")
        res = self.client.get(reverse("enrollment:export_roster_csv", kwargs={"offering_id": offering.id}))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", res["Content-Disposition"])

        content = res.content.decode("utf-8")
        self.assertIn("USN / Register Number", content)
        self.assertIn("1RV24CS100", content)
        self.assertIn("CS101", content)

    def test_attendance_and_assessment_extensibility(self):
        """Phase 8: Extensibility verification for Attendance and Assessment models."""
        from datetime import date
        from enrollment.models import AttendanceSession, AttendanceRecord, AssessmentComponent, StudentMark

        offering = CourseOffering.objects.create(
            course=self.course1,
            batch=self.batch,
            faculty=self.faculty_prof,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )
        enr = StudentCourseEnrollment.objects.create(student=self.students[0], course_offering=offering)

        # 1. Attendance session & record
        session = AttendanceSession.objects.create(
            course_offering=offering,
            date=date.today(),
            slot=1,
            topic_covered="Binary Trees and Traversal Algorithms",
        )
        record = AttendanceRecord.objects.create(session=session, student=self.students[0], is_present=True)
        self.assertEqual(session.records.count(), 1)
        self.assertTrue(record.is_present)

        # 2. CIE Assessment component & student marks
        comp = AssessmentComponent.objects.create(
            course_offering=offering,
            name="CIE Test 1",
            max_marks=Decimal("50.00"),
            weightage_percentage=Decimal("20.00"),
        )
        mark = StudentMark.objects.create(component=comp, enrollment=enr, marks_obtained=Decimal("45.50"))
        self.assertEqual(comp.marks.count(), 1)
        self.assertEqual(mark.marks_obtained, Decimal("45.50"))

    def test_mark_attendance_view_flow(self):
        """Faculty can mark classroom attendance and cumulative percentage updates."""
        from datetime import date
        from enrollment.models import AttendanceSession, AttendanceRecord

        offering = CourseOffering.objects.create(
            course=self.course1,
            batch=self.batch,
            faculty=self.faculty_prof,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )
        enr1 = StudentCourseEnrollment.objects.create(student=self.students[0], course_offering=offering)
        enr2 = StudentCourseEnrollment.objects.create(student=self.students[1], course_offering=offering)

        self.client.login(username="fac_smith", password="pass123")
        post_data = {
            "date": date.today().isoformat(),
            "slot": "2",
            "topic_covered": "Graph Traversal BFS and DFS",
            f"present_{self.students[0].id}": "on",  # Student 0 present, Student 1 absent
        }
        res = self.client.post(
            reverse("enrollment:mark_attendance", kwargs={"offering_id": offering.id}),
            post_data,
        )
        self.assertEqual(res.status_code, 302)

        # Verify records and recalculated percentages
        session = AttendanceSession.objects.get(course_offering=offering)
        self.assertEqual(session.slot, 2)
        self.assertTrue(AttendanceRecord.objects.get(session=session, student=self.students[0]).is_present)
        self.assertFalse(AttendanceRecord.objects.get(session=session, student=self.students[1]).is_present)

        enr1.refresh_from_db()
        enr2.refresh_from_db()
        self.assertEqual(enr1.attendance_percentage, Decimal("100.00"))
        self.assertEqual(enr2.attendance_percentage, Decimal("0.00"))

    def test_enter_marks_view_flow(self):
        """Faculty can input CIE test marks and see them persisted."""
        offering = CourseOffering.objects.create(
            course=self.course1,
            batch=self.batch,
            faculty=self.faculty_prof,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )
        enr = StudentCourseEnrollment.objects.create(student=self.students[0], course_offering=offering)
        comp = AssessmentComponent.objects.create(
            course_offering=offering, name="CIE-1", max_marks=Decimal("50.00")
        )

        self.client.login(username="fac_smith", password="pass123")
        res = self.client.post(
            reverse("enrollment:enter_marks", kwargs={"component_id": comp.id}),
            {f"mark_{enr.id}": "47.5"},
        )
        mark = StudentMark.objects.get(component=comp, enrollment=enr)
        self.assertEqual(mark.marks_obtained, Decimal("47.50"))

    def test_enter_course_grades_view_flow(self):
        """Faculty can assign final letter grades to enrolled students."""
        offering = CourseOffering.objects.create(
            course=self.course1,
            batch=self.batch,
            faculty=self.faculty_prof,
            academic_year="2024-2025",
            term="ODD",
            section="A",
        )
        enr = StudentCourseEnrollment.objects.create(student=self.students[0], course_offering=offering)

        self.client.login(username="fac_smith", password="pass123")
        res_get = self.client.get(reverse("enrollment:enter_grades", kwargs={"offering_id": offering.id}))
        self.assertEqual(res_get.status_code, 200)

        res_post = self.client.post(
            reverse("enrollment:enter_grades", kwargs={"offering_id": offering.id}),
            {f"grade_{enr.id}": "A+"},
        )
        self.assertEqual(res_post.status_code, 302)

        enr.refresh_from_db()
        self.assertEqual(enr.grade, "A+")



