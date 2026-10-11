"""
Academic domain models representing the institutional hierarchy and curriculum structure.

Hierarchy:
  College (1) ──> (N) Department (1) ──> (N) Program (1) ──> (N) Scheme (1) ──> (N) Semester (1) ──> (N) Course
                           │                    │
                           │                    └──> (N) Batch (1) ──> (N) StudentProfile
                           └──> (N) FacultyProfile
"""

import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class College(models.Model):
    """Apex institutional entity representing the college or university."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique institutional identifier (e.g., 'MIT', 'RVCE', 'IITB').",
    )
    name = models.CharField(
        max_length=200,
        help_text="Full legal name of the institution.",
    )
    established_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Year the institution was founded.",
    )
    address = models.TextField(
        blank=True,
        help_text="Full postal campus address.",
    )
    website = models.URLField(
        blank=True,
        help_text="Official institution website URL.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "College"
        verbose_name_plural = "Colleges"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(models.Model):
    """Academic department within a college (e.g., Computer Science, Mechanical Eng)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    college = models.ForeignKey(
        College,
        on_delete=models.PROTECT,
        related_name="departments",
        help_text="Parent college governing this department.",
    )
    code = models.CharField(
        max_length=20,
        help_text="Department short code (e.g., 'CSE', 'ECE', 'MECH').",
    )
    name = models.CharField(
        max_length=200,
        help_text="Full department title (e.g., 'Department of Computer Science & Engineering').",
    )
    description = models.TextField(
        blank=True,
        help_text="Brief overview or mission statement.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        unique_together = [("college", "code")]
        ordering = ["college", "code"]

    def __str__(self):
        return f"{self.name} [{self.code}]"


class Program(models.Model):
    """Degree program offered by a department (e.g., B.Tech in CSE, M.Tech, MCA)."""

    class DegreeType(models.TextChoices):
        UG = "UG", "Undergraduate (UG)"
        PG = "PG", "Postgraduate (PG)"
        DIPLOMA = "DIPLOMA", "Diploma"
        PHD = "PHD", "Doctorate / PhD"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="programs",
        help_text="Department administering this degree program.",
    )
    code = models.CharField(
        max_length=20,
        help_text="Program code (e.g., 'BTECH-CS', 'MCA', 'MTECH-DS').",
    )
    name = models.CharField(
        max_length=200,
        help_text="Full program title (e.g., 'Bachelor of Technology in Computer Science').",
    )
    degree_type = models.CharField(
        max_length=20,
        choices=DegreeType.choices,
        default=DegreeType.UG,
        help_text="Academic tier of the degree program.",
    )
    duration_years = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text="Normal nominal program duration in calendar years.",
    )
    total_semesters = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Total number of academic semesters required for degree completion.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Program"
        verbose_name_plural = "Programs"
        unique_together = [("department", "code")]
        ordering = ["department", "code"]

    def __str__(self):
        return f"{self.name} ({self.code}) — {self.get_degree_type_display()}"


class Scheme(models.Model):
    """Academic curriculum regulation / syllabus scheme (e.g., 2024 CBCS Scheme)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="schemes",
        help_text="Degree program this regulation scheme belongs to.",
    )
    code = models.CharField(
        max_length=30,
        help_text="Scheme identifier (e.g., 'SCH2024', 'REG-2022', 'CBCS-2021').",
    )
    name = models.CharField(
        max_length=200,
        help_text="Descriptive scheme title (e.g., '2024 Outcome Based CBCS Curriculum').",
    )
    effective_year = models.PositiveIntegerField(
        help_text="Academic year from which this scheme becomes applicable.",
    )
    total_credits_required = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=160.00,
        validators=[MinValueValidator(20.0), MaxValueValidator(300.0)],
        help_text="Total credits required to graduate under this curriculum.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this scheme is currently active for ongoing or incoming cohorts.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Curriculum Scheme"
        verbose_name_plural = "Curriculum Schemes"
        unique_together = [("program", "code")]
        ordering = ["program", "-effective_year", "code"]

    def __str__(self):
        status = "Active" if self.is_active else "Archived"
        return f"{self.program.code} — {self.name} [{self.code}] ({status})"


class Semester(models.Model):
    """Academic semester / term under a specific curriculum scheme."""

    class SemesterType(models.TextChoices):
        ODD = "ODD", "Odd Semester"
        EVEN = "EVEN", "Even Semester"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.CASCADE,
        related_name="semesters",
        help_text="Parent regulation scheme defining this semester.",
    )
    semester_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Sequential semester number (1, 2, 3, etc.).",
    )
    semester_type = models.CharField(
        max_length=10,
        choices=SemesterType.choices,
        help_text="Determines whether this is an odd or even calendar term.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Semester"
        verbose_name_plural = "Semesters"
        unique_together = [("scheme", "semester_number")]
        ordering = ["scheme", "semester_number"]

    def clean(self):
        # Auto-compute or validate semester_type based on parity
        if self.semester_number:
            expected_type = self.SemesterType.ODD if self.semester_number % 2 == 1 else self.SemesterType.EVEN
            if not self.semester_type:
                self.semester_type = expected_type

    def __str__(self):
        return f"{self.scheme.code} — Semester {self.semester_number} ({self.get_semester_type_display()})"


class Course(models.Model):
    """Individual academic course / subject taught within a semester."""

    class CourseType(models.TextChoices):
        CORE = "CORE", "Core Theory"
        LAB = "LAB", "Practical / Laboratory"
        ELECTIVE = "ELECTIVE", "Professional Elective"
        OPEN_ELECTIVE = "OPEN_ELECTIVE", "Open Elective"
        PROJECT = "PROJECT", "Project / Capstone / Seminar"
        AUDIT = "AUDIT", "Audit (Non-Credit)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    semester = models.ForeignKey(
        Semester,
        on_delete=models.PROTECT,
        related_name="courses",
        help_text="Curriculum semester this course belongs to.",
    )
    code = models.CharField(
        max_length=30,
        help_text="Unique course code (e.g., 'CS301', 'MAT201', 'CS502L').",
    )
    title = models.CharField(
        max_length=200,
        help_text="Full course title (e.g., 'Data Structures and Algorithms').",
    )
    course_type = models.CharField(
        max_length=20,
        choices=CourseType.choices,
        default=CourseType.CORE,
        help_text="Pedagogical classification of the course.",
    )
    credits = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=3.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(12.0)],
        help_text="Academic credit weight assigned to this course.",
    )
    lecture_hours = models.PositiveSmallIntegerField(
        default=3,
        help_text="Lecture hours per week (L).",
    )
    tutorial_hours = models.PositiveSmallIntegerField(
        default=0,
        help_text="Tutorial hours per week (T).",
    )
    practical_hours = models.PositiveSmallIntegerField(
        default=0,
        help_text="Practical / Lab hours per week (P).",
    )
    syllabus_summary = models.TextField(
        blank=True,
        help_text="Overview of syllabus units, course outcomes, and reference textbooks.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        unique_together = [("semester", "code")]
        ordering = ["semester", "code"]

    @property
    def ltp_structure(self):
        """Returns the L-T-P notation (e.g., '3-0-2')."""
        return f"{self.lecture_hours}-{self.tutorial_hours}-{self.practical_hours}"

    def __str__(self):
        return f"{self.code} — {self.title} ({self.credits} Credits)"


class Batch(models.Model):
    """Student cohort admitted in a specific calendar year under a curriculum scheme."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="batches",
        help_text="Degree program this cohort is enrolled in.",
    )
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.PROTECT,
        related_name="batches",
        help_text="Curriculum scheme governing this cohort's degree syllabus.",
    )
    name = models.CharField(
        max_length=100,
        help_text="Descriptive cohort name (e.g., '2023-2027 CSE Batch A').",
    )
    admission_year = models.PositiveIntegerField(
        help_text="Year in which this cohort was admitted (e.g., 2023).",
    )
    graduation_year = models.PositiveIntegerField(
        help_text="Expected graduation year (e.g., 2027).",
    )
    current_semester = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Current active semester for this student cohort.",
    )
    is_graduated = models.BooleanField(
        default=False,
        help_text="Mark True once this cohort has completed all program requirements.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Batch / Cohort"
        verbose_name_plural = "Batches & Cohorts"
        unique_together = [("program", "admission_year", "name")]
        ordering = ["program", "-admission_year", "name"]

    def clean(self):
        # 1. Scheme relational integrity check: Scheme must belong to the selected Program
        if self.scheme_id and self.program_id:
            if self.scheme.program_id != self.program_id:
                raise ValidationError({
                    "scheme": (
                        f"The selected scheme '{self.scheme.code}' belongs to program "
                        f"'{self.scheme.program.code}', not '{self.program.code}'."
                    )
                })

        # 2. Timeline logical sanity check
        if self.admission_year and self.graduation_year:
            if self.graduation_year < self.admission_year:
                raise ValidationError({
                    "graduation_year": "Expected graduation year cannot be earlier than admission year."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} [{self.program.code}] ({self.admission_year}–{self.graduation_year})"


class FacultyProfile(models.Model):
    """Academic staff profile linked 1-to-1 with a User entity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="faculty_profile",
        help_text="User account associated with this faculty member.",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="faculty_members",
        help_text="Parent department the faculty member is affiliated with.",
    )
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique institutional employee code (e.g., 'EMP-CS-104').",
    )
    designation = models.CharField(
        max_length=100,
        help_text="Academic title (e.g., 'Professor', 'Associate Professor', 'Assistant Professor').",
    )
    qualification = models.CharField(
        max_length=150,
        blank=True,
        help_text="Highest educational degree (e.g., 'Ph.D. in Computer Science', 'M.Tech').",
    )
    joining_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the faculty member joined the institution.",
    )
    cabin_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Campus office / cabin location (e.g., 'Admin Block Room 304').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Faculty Profile"
        verbose_name_plural = "Faculty Profiles"
        ordering = ["department", "user__last_name", "user__first_name"]

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return f"{self.full_name} — {self.designation} ({self.department.code})"


class StudentProfile(models.Model):
    """Student academic profile linked 1-to-1 with a User entity and assigned to a Batch."""

    class StudentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active / Enrolled"
        DETAINED = "DETAINED", "Detained / Academic Hold"
        GRADUATED = "GRADUATED", "Graduated"
        DROPPED = "DROPPED", "Dropped Out"
        INACTIVE = "INACTIVE", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        help_text="User account associated with this student.",
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        related_name="students",
        help_text="Cohort batch this student belongs to.",
    )
    register_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="University seat number / unique student register number (e.g., '1RV23CS045').",
    )
    roll_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Classroom roll number (e.g., 'CS-45').",
    )
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
        help_text="Current academic status of the student.",
    )
    admission_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of formal admission into the college.",
    )
    emergency_contact = models.CharField(
        max_length=20,
        blank=True,
        help_text="Emergency contact phone number.",
    )
    blood_group = models.CharField(
        max_length=10,
        blank=True,
        help_text="Student's blood group (e.g., 'O+', 'A+').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ["batch", "register_number"]

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def department(self):
        return self.batch.program.department

    @property
    def program(self):
        return self.batch.program

    def __str__(self):
        return f"{self.register_number} — {self.full_name} ({self.batch.name})"
