"""
Integration tests for role portals and academic hierarchy views.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from academics.models import College, Department, Program, Scheme, Semester, Course, Batch, StudentProfile, FacultyProfile
from enrollment.models import CourseOffering, StudentCourseEnrollment, TimetableEntry, CourseMaterial


class PortalIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # College and Department
        self.college = College.objects.create(code="RVCE", name="R.V. College of Engineering")
        self.dept = Department.objects.create(college=self.college, code="CSE", name="Computer Science")

        # Program, Scheme, Semester, Course
        self.prog = Program.objects.create(
            department=self.dept, code="BTECH-CS", name="B.Tech Computer Science"
        )
        self.scheme = Scheme.objects.create(
            program=self.prog, code="SCH2024", name="2024 Scheme", effective_year=2024
        )
        self.sem = Semester.objects.create(scheme=self.scheme, semester_number=1, semester_type="ODD")
        self.course = Course.objects.create(
            semester=self.sem, code="CS101", title="Python Programming", credits=Decimal("4.00")
        )

        # Batch
        self.batch = Batch.objects.create(
            program=self.prog, scheme=self.scheme, name="2024 Batch A", admission_year=2024, graduation_year=2028
        )

        # Users
        self.admin_user = User.objects.create_superuser("admin_user", "admin@rvce.edu.in", "pass123", role=User.Role.COLLEGE_ADMIN)
        self.dept_user = User.objects.create_user("dept_user", "dept@rvce.edu.in", "pass123", role=User.Role.DEPT_ADMIN, assigned_department=self.dept)
        self.faculty_user = User.objects.create_user("faculty_user", "faculty@rvce.edu.in", "pass123", role=User.Role.FACULTY)
        self.faculty_prof = FacultyProfile.objects.create(user=self.faculty_user, department=self.dept, employee_id="EMP-01", designation="Assistant Professor")
        self.student_user = User.objects.create_user("student_user", "student@rvce.edu.in", "pass123", role=User.Role.STUDENT)
        self.student_prof = StudentProfile.objects.create(user=self.student_user, batch=self.batch, register_number="1RV24CS001")

        # Offering & Enrollment
        self.offering = CourseOffering.objects.create(
            course=self.course, batch=self.batch, faculty=self.faculty_prof, academic_year="2024-2025", term="ODD", section="A"
        )
        self.enrollment = StudentCourseEnrollment.objects.create(student=self.student_prof, course_offering=self.offering)

    def test_admin_dashboard_access(self):
        self.client.login(username="admin_user", password="pass123")
        res = self.client.get(reverse("portal:admin_dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "R.V. College of Engineering")
        self.assertContains(res, "Computer Science")

    def test_department_dashboard_access(self):
        self.client.login(username="dept_user", password="pass123")
        res = self.client.get(reverse("portal:department_dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Computer Science")
        self.assertContains(res, "BTECH-CS")

    def test_faculty_portal_access(self):
        self.client.login(username="faculty_user", password="pass123")
        res = self.client.get(reverse("portal:faculty_portal"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "CS101")
        self.assertContains(res, "Python Programming")

    def test_student_portal_access(self):
        self.client.login(username="student_user", password="pass123")
        res = self.client.get(reverse("portal:student_portal"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "1RV24CS001")
        self.assertContains(res, "CS101")

    def test_hierarchy_explorer_view(self):
        self.client.login(username="admin_user", password="pass123")
        res = self.client.get(reverse("academics:hierarchy_explorer"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Interactive Curriculum Hierarchy Explorer")
        self.assertContains(res, "CS101")

    def test_cascading_api_endpoints(self):
        self.client.login(username="admin_user", password="pass123")

        # Dept -> Programs
        res = self.client.get(reverse("academics:api_programs", kwargs={"dept_id": self.dept.id}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(any(p["code"] == "BTECH-CS" for p in data["results"]))

        # Program -> Schemes
        res = self.client.get(reverse("academics:api_schemes", kwargs={"prog_id": self.prog.id}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(any(s["code"] == "SCH2024" for s in data["results"]))

        # Scheme -> Semesters
        res = self.client.get(reverse("academics:api_semesters", kwargs={"scheme_id": self.scheme.id}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(any(s["semester_number"] == 1 for s in data["results"]))

        # Semester -> Courses
        res = self.client.get(reverse("academics:api_courses", kwargs={"semester_id": self.sem.id}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(any(c["code"] == "CS101" for c in data["results"]))

    def test_attendance_alerts_view(self):
        """Attendance shortage alert analytics shows critical, warning, and compliant student records."""
        from decimal import Decimal
        # Set student attendance to 68% (critical shortage)
        self.enrollment.attendance_percentage = Decimal("68.00")
        self.enrollment.save()

        # 1. College admin access
        self.client.login(username="admin_user", password="pass123")
        res = self.client.get(reverse("portal:attendance_alerts"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Attendance Shortage &amp; Exam Ineligibility Alerts")
        self.assertContains(res, "1RV24CS001")
        self.assertContains(res, "INELIGIBLE (SHORTAGE)")

        # 2. Filter by critical
        res_crit = self.client.get(reverse("portal:attendance_alerts") + "?status=critical")
        self.assertEqual(res_crit.status_code, 200)
        self.assertContains(res_crit, "1RV24CS001")

        # 3. Dept admin access scoped
        self.client.login(username="dept_user", password="pass123")
        res_dept = self.client.get(reverse("portal:attendance_alerts"))
        self.assertEqual(res_dept.status_code, 200)
        self.assertContains(res_dept, "1RV24CS001")

    def test_timetable_and_materials_in_portals(self):
        """Timetable slots and learning materials render properly on faculty and student portals."""
        from datetime import time
        # Create timetable slot
        slot = TimetableEntry.objects.create(
            course_offering=self.offering,
            day_of_week="MON",
            slot_number=1,
            start_time=time(9, 0),
            end_time=time(10, 0),
            classroom="LH-101",
        )
        # Create course material
        mat = CourseMaterial.objects.create(
            course_offering=self.offering,
            title="Lecture 1: Computational Thinking",
            description="Introduction to algorithm design.",
            material_type=CourseMaterial.MaterialType.LECTURE_NOTES,
            resource_url="https://example.com/lecture1.pdf",
        )

        # Faculty portal check
        self.client.login(username="faculty_user", password="pass123")
        res_fac = self.client.get(reverse("portal:faculty_portal"))
        self.assertEqual(res_fac.status_code, 200)
        self.assertContains(res_fac, "My Weekly Teaching Schedule")
        self.assertContains(res_fac, "LH-101")

        # Student portal check
        self.client.login(username="student_user", password="pass123")
        res_stud = self.client.get(reverse("portal:student_portal"))
        self.assertEqual(res_stud.status_code, 200)
        self.assertContains(res_stud, "Weekly Class Timetable")
        self.assertContains(res_stud, "Lecture 1: Computational Thinking")
        self.assertContains(res_stud, "Access Resource")

    def test_academic_notice_board_and_audience_filtering(self):
        """Campus Notice Board creation, audience filtering, and detail views."""
        from portal.models import AcademicNotice

        # Admin publishes institution-wide notice
        self.client.login(username="admin_user", password="pass123")
        res_create = self.client.post(reverse("portal:notice_create"), {
            "title": "Annual Tech Symposium 2026",
            "content": "All students and faculty are invited to register projects.",
            "category": AcademicNotice.Category.EVENT,
            "priority": AcademicNotice.Priority.IMPORTANT,
            "target_role": AcademicNotice.TargetRole.ALL,
            "is_active": True,
        })
        self.assertEqual(res_create.status_code, 302)
        notice_all = AcademicNotice.objects.get(title="Annual Tech Symposium 2026")
        self.assertEqual(notice_all.target_role, AcademicNotice.TargetRole.ALL)

        # Create faculty-only notice
        notice_fac = AcademicNotice.objects.create(
            title="Faculty Evaluation Meeting",
            content="Mandatory meeting for staff.",
            category=AcademicNotice.Category.CIRCULAR,
            target_role=AcademicNotice.TargetRole.FACULTY,
            department=self.dept,
            publisher=self.admin_user,
            is_active=True,
        )

        # Faculty visits notice list — sees both notices
        self.client.login(username="faculty_user", password="pass123")
        res_fac = self.client.get(reverse("portal:notice_list"))
        self.assertEqual(res_fac.status_code, 200)
        self.assertContains(res_fac, "Annual Tech Symposium 2026")
        self.assertContains(res_fac, "Faculty Evaluation Meeting")

        # Student visits notice list — sees All notice, does NOT see Faculty notice
        self.client.login(username="student_user", password="pass123")
        res_stud = self.client.get(reverse("portal:notice_list"))
        self.assertEqual(res_stud.status_code, 200)
        self.assertContains(res_stud, "Annual Tech Symposium 2026")
        self.assertNotContains(res_stud, "Faculty Evaluation Meeting")

        # Detail view for authorized notice
        res_detail = self.client.get(reverse("portal:notice_detail", args=[notice_all.id]))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Annual Tech Symposium 2026")


