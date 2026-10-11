"""
Unit tests validating Phase 2 domain models and relational integrity guarantees.

Tests verify:
1. Database constraints reject duplicate course codes within the same semester.
2. Attempting to delete a Department that contains Programs raises a ProtectedError.
3. Validation in Batch.clean() prevents assigning a Scheme belonging to a different Program.
4. Cascading protection across institutional entities.
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from academics.models import (
    College,
    Department,
    Program,
    Scheme,
    Semester,
    Course,
    Batch,
    FacultyProfile,
    StudentProfile,
)
from accounts.models import User
from enrollment.models import CourseOffering, StudentCourseEnrollment


class AcademicRelationalIntegrityTestCase(TestCase):
    def setUp(self):
        # Base Apex entity
        self.college = College.objects.create(
            code="RVCE",
            name="R.V. College of Engineering",
            established_year=1963,
            address="Mysore Road, Bengaluru",
            website="https://www.rvce.edu.in",
        )

        # Department
        self.department = Department.objects.create(
            college=self.college,
            code="CSE",
            name="Computer Science & Engineering",
        )

        # Second Department for cross-program testing
        self.ece_dept = Department.objects.create(
            college=self.college,
            code="ECE",
            name="Electronics & Communication Engineering",
        )

        # Degree Programs
        self.cse_program = Program.objects.create(
            department=self.department,
            code="BTECH-CS",
            name="Bachelor of Technology in Computer Science",
            degree_type=Program.DegreeType.UG,
            duration_years=4,
            total_semesters=8,
        )

        self.ece_program = Program.objects.create(
            department=self.ece_dept,
            code="BTECH-EC",
            name="Bachelor of Technology in Electronics",
            degree_type=Program.DegreeType.UG,
            duration_years=4,
            total_semesters=8,
        )

        # Curriculum Schemes
        self.cse_scheme = Scheme.objects.create(
            program=self.cse_program,
            code="SCH2024",
            name="2024 CBCS Curriculum",
            effective_year=2024,
            total_credits_required=Decimal("160.00"),
            is_active=True,
        )

        self.ece_scheme = Scheme.objects.create(
            program=self.ece_program,
            code="SCH2024-EC",
            name="2024 ECE Curriculum",
            effective_year=2024,
            total_credits_required=Decimal("160.00"),
            is_active=True,
        )

        # Semester
        self.semester_1 = Semester.objects.create(
            scheme=self.cse_scheme,
            semester_number=1,
            semester_type=Semester.SemesterType.ODD,
        )

        # Course
        self.course_ds = Course.objects.create(
            semester=self.semester_1,
            code="CS101",
            title="Programming and Data Structures",
            course_type=Course.CourseType.CORE,
            credits=Decimal("4.00"),
            lecture_hours=3,
            tutorial_hours=0,
            practical_hours=2,
        )

    def test_duplicate_course_code_in_same_semester_rejected(self):
        """Criterion 1: Database constraint must reject duplicate course code in the same semester."""
        with self.assertRaises(IntegrityError):
            Course.objects.create(
                semester=self.semester_1,
                code="CS101",  # Duplicate code in semester_1
                title="Another Course With Same Code",
                credits=Decimal("3.00"),
            )

    def test_department_deletion_protection(self):
        """Criterion 2: Deleting a Department that contains Programs must raise ProtectedError."""
        with self.assertRaises(ProtectedError):
            self.department.delete()

    def test_college_deletion_protection(self):
        """Deleting a College that contains Departments must raise ProtectedError."""
        with self.assertRaises(ProtectedError):
            self.college.delete()

    def test_batch_scheme_program_mismatch_validation(self):
        """Criterion 3: Batch.clean() must prevent assigning a Scheme belonging to a different Program."""
        # Attempting to assign ECE scheme to CSE program batch
        invalid_batch = Batch(
            program=self.cse_program,
            scheme=self.ece_scheme,  # Mismatch: belongs to ece_program
            name="2024-2028 CSE Invalid",
            admission_year=2024,
            graduation_year=2028,
            current_semester=1,
        )

        with self.assertRaises(ValidationError) as context:
            invalid_batch.clean()

        self.assertIn("scheme", context.exception.message_dict)

    def test_valid_batch_creation_succeeds(self):
        """Valid batch with matching program and scheme saves cleanly."""
        valid_batch = Batch.objects.create(
            program=self.cse_program,
            scheme=self.cse_scheme,
            name="2024-2028 CSE Alpha",
            admission_year=2024,
            graduation_year=2028,
            current_semester=1,
        )
        self.assertEqual(valid_batch.name, "2024-2028 CSE Alpha")
        self.assertEqual(valid_batch.current_semester, 1)

    def test_batch_graduation_year_before_admission_year_rejected(self):
        """Batch graduation year before admission year must be rejected."""
        invalid_batch = Batch(
            program=self.cse_program,
            scheme=self.cse_scheme,
            name="2024 Time Travel Batch",
            admission_year=2024,
            graduation_year=2020,  # Invalid
        )
        with self.assertRaises(ValidationError) as context:
            invalid_batch.clean()

        self.assertIn("graduation_year", context.exception.message_dict)

    def test_student_and_faculty_profiles(self):
        """Faculty and Student profiles link correctly with roles and constraints."""
        # Create faculty user
        faculty_user = User.objects.create_user(
            username="faculty_smith",
            password="password123",
            role=User.Role.FACULTY,
            first_name="John",
            last_name="Smith",
            email="smith@rvce.edu.in",
        )
        faculty_profile = FacultyProfile.objects.create(
            user=faculty_user,
            department=self.department,
            employee_id="EMP-CS-001",
            designation="Associate Professor",
            qualification="Ph.D. in Computer Science",
        )

        # Create batch
        batch = Batch.objects.create(
            program=self.cse_program,
            scheme=self.cse_scheme,
            name="2024-2028 CSE Beta",
            admission_year=2024,
            graduation_year=2028,
        )

        # Create student user
        student_user = User.objects.create_user(
            username="student_alice",
            password="password123",
            role=User.Role.STUDENT,
            first_name="Alice",
            last_name="Johnson",
            email="alice@rvce.edu.in",
        )
        student_profile = StudentProfile.objects.create(
            user=student_user,
            batch=batch,
            register_number="1RV24CS001",
            roll_number="CS-01",
            status=StudentProfile.StudentStatus.ACTIVE,
        )

        # Verify property resolutions
        self.assertEqual(faculty_user.department, self.department)
        self.assertEqual(student_user.department, self.department)
        self.assertEqual(student_profile.program, self.cse_program)

        # Test CourseOffering & Enrollment
        offering = CourseOffering.objects.create(
            course=self.course_ds,
            batch=batch,
            faculty=faculty_profile,
            academic_year="2024-2025",
            term=CourseOffering.Term.ODD,
            section="A",
        )
        enrollment = StudentCourseEnrollment.objects.create(
            student=student_profile,
            course_offering=offering,
            status=StudentCourseEnrollment.EnrollmentStatus.ENROLLED,
        )

        self.assertEqual(enrollment.student, student_profile)
        self.assertEqual(enrollment.course_offering, offering)

        # Prevent duplicate enrollment in the same offering
        with self.assertRaises(IntegrityError):
            StudentCourseEnrollment.objects.create(
                student=student_profile,
                course_offering=offering,
            )
