"""
Operational course offering and student enrollment models.

Bridges static curriculum courses with live batches, assigned instructors,
academic years, and individual student enrollments.
"""

import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class CourseOffering(models.Model):
    """
    Live semester offering of an academic course to a specific student batch.

    Links a course from the curriculum with an assigned faculty instructor,
    academic calendar term, and classroom section.
    """

    class Term(models.TextChoices):
        ODD = "ODD", "Odd Term"
        EVEN = "EVEN", "Even Term"
        SUMMER = "SUMMER", "Summer Term"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        "academics.Course",
        on_delete=models.PROTECT,
        related_name="offerings",
        help_text="Curriculum course being offered.",
    )
    batch = models.ForeignKey(
        "academics.Batch",
        on_delete=models.PROTECT,
        related_name="course_offerings",
        help_text="Student batch / cohort receiving this course.",
    )
    faculty = models.ForeignKey(
        "academics.FacultyProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_offerings",
        help_text="Assigned faculty instructor / course coordinator.",
    )
    academic_year = models.CharField(
        max_length=20,
        help_text="Academic year string (e.g., '2024-2025', '2025-2026').",
    )
    term = models.CharField(
        max_length=10,
        choices=Term.choices,
        default=Term.ODD,
        help_text="Calendar semester term (Odd/Even/Summer).",
    )
    section = models.CharField(
        max_length=10,
        default="A",
        help_text="Classroom section division (e.g., 'A', 'B', 'CS-1').",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this offering is currently in-progress.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Course Offering"
        verbose_name_plural = "Course Offerings"
        unique_together = [("course", "batch", "academic_year", "term", "section")]
        ordering = ["-academic_year", "term", "course__code", "section"]

    def __str__(self):
        faculty_name = self.faculty.full_name if self.faculty else "Unassigned"
        return f"{self.course.code} (Sec {self.section}) — {self.academic_year} {self.term} [{faculty_name}]"


class StudentCourseEnrollment(models.Model):
    """Individual student enrollment record in a specific course offering."""

    class EnrollmentStatus(models.TextChoices):
        ENROLLED = "ENROLLED", "Enrolled"
        DROPPED = "DROPPED", "Dropped"
        COMPLETED = "COMPLETED", "Completed"
        AUDIT = "AUDIT", "Audit Only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="enrollments",
        help_text="Enrolled student profile.",
    )
    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.CASCADE,
        related_name="enrollments",
        help_text="Specific course offering section.",
    )
    enrolled_on = models.DateField(
        auto_now_add=True,
        help_text="Date on which the student was enrolled.",
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
        help_text="Current state of the student's enrollment in this course.",
    )
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Aggregated percentage attendance recorded (0.00% to 100.00%).",
    )
    grade = models.CharField(
        max_length=5,
        blank=True,
        help_text="Final awarded letter grade (e.g., 'A+', 'B', 'F').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Course Enrollment"
        verbose_name_plural = "Student Course Enrollments"
        unique_together = [("student", "course_offering")]
        ordering = ["student__register_number", "course_offering__course__code"]

    def __str__(self):
        return f"{self.student.register_number} ── {self.course_offering.course.code} ({self.get_status_display()})"


# ── Extensibility Modules: Attendance & Internal Marks ────────────────────────

class AttendanceSession(models.Model):
    """Specific lecture/lab session conducted for a course offering."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
        help_text="Course offering this attendance session belongs to.",
    )
    date = models.DateField(help_text="Date on which the session took place.")
    slot = models.PositiveSmallIntegerField(
        default=1,
        help_text="Classroom timetable period / slot number (1, 2, 3, etc.).",
    )
    topic_covered = models.CharField(
        max_length=200,
        blank=True,
        help_text="Lecture topic or lab experiment performed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Attendance Session"
        verbose_name_plural = "Attendance Sessions"
        unique_together = [("course_offering", "date", "slot")]
        ordering = ["-date", "-slot"]

    def __str__(self):
        return f"{self.course_offering.course.code} &bull; {self.date} (Slot {self.slot})"


class AttendanceRecord(models.Model):
    """Individual student present/absent mark for an attendance session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records",
    )
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    is_present = models.BooleanField(
        default=True,
        help_text="True if present, False if absent.",
    )
    remarks = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional remarks (e.g. 'On Duty', 'Medical Leave').",
    )

    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        unique_together = [("session", "student")]

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.register_number} — {status}"


class AssessmentComponent(models.Model):
    """Continuous Internal Evaluation (CIE) or test component for a course offering."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.CASCADE,
        related_name="assessment_components",
    )
    name = models.CharField(
        max_length=100,
        help_text="Evaluation title (e.g., 'Internal Test 1', 'Lab Assignment 1', 'Seminar').",
    )
    max_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        help_text="Maximum scorables marks for this assessment.",
    )
    weightage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        help_text="Percentage weightage contributing to final internal calculation.",
    )
    conducted_date = models.DateField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Assessment Component"
        verbose_name_plural = "Assessment Components"
        unique_together = [("course_offering", "name")]

    def __str__(self):
        return f"{self.course_offering.course.code} — {self.name} (Max {self.max_marks})"


class StudentMark(models.Model):
    """Marks obtained by an enrolled student in an assessment component."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    component = models.ForeignKey(
        AssessmentComponent,
        on_delete=models.CASCADE,
        related_name="marks",
    )
    enrollment = models.ForeignKey(
        StudentCourseEnrollment,
        on_delete=models.CASCADE,
        related_name="marks",
    )
    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Actual score obtained by the student.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Student Assessment Mark"
        verbose_name_plural = "Student Assessment Marks"
        unique_together = [("component", "enrollment")]

    def __str__(self):
        return f"{self.enrollment.student.register_number} — {self.component.name}: {self.marks_obtained}/{self.component.max_marks}"


class TimetableEntry(models.Model):
    """Weekly class schedule mapping course offerings to day, time slot, and classroom."""

    class DayOfWeek(models.TextChoices):
        MONDAY = "MON", "Monday"
        TUESDAY = "TUE", "Tuesday"
        WEDNESDAY = "WED", "Wednesday"
        THURSDAY = "THU", "Thursday"
        FRIDAY = "FRI", "Friday"
        SATURDAY = "SAT", "Saturday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.CASCADE,
        related_name="timetable_entries",
        help_text="Course offering scheduled in this slot.",
    )
    day_of_week = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
        help_text="Day of the week.",
    )
    slot_number = models.PositiveSmallIntegerField(
        default=1,
        help_text="Period slot number (1 through 8).",
    )
    start_time = models.TimeField(help_text="Slot start time (e.g., 09:00:00).")
    end_time = models.TimeField(help_text="Slot end time (e.g., 10:00:00).")
    classroom = models.CharField(
        max_length=50,
        default="LH-101",
        help_text="Lecture hall, auditorium, or lab room.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Timetable Entry"
        verbose_name_plural = "Timetable Entries"
        unique_together = [("course_offering", "day_of_week", "slot_number")]
        ordering = ["day_of_week", "slot_number"]

    def __str__(self):
        return f"{self.get_day_of_week_display()} Slot {self.slot_number} • {self.course_offering.course.code} ({self.classroom})"


class CourseMaterial(models.Model):
    """Digital learning resource, syllabus, lecture notes, or assignment upload."""

    class MaterialType(models.TextChoices):
        SYLLABUS = "SYLLABUS", "Syllabus & Lesson Plan"
        LECTURE_NOTES = "NOTES", "Lecture Slides & Notes"
        ASSIGNMENT = "ASSIGNMENT", "Assignment & Question Bank"
        REFERENCE = "REFERENCE", "Reference Link & Reading Material"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.CASCADE,
        related_name="materials",
        help_text="Course offering this material belongs to.",
    )
    title = models.CharField(max_length=200, help_text="Resource title (e.g., 'Unit 1: Graph Theory Notes').")
    description = models.TextField(blank=True, help_text="Detailed summary or instructions for students.")
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.LECTURE_NOTES,
        help_text="Categorization of the learning resource.",
    )
    resource_url = models.CharField(
        max_length=500,
        help_text="External URL, drive link, or document path.",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Course Learning Material"
        verbose_name_plural = "Course Learning Materials"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.course_offering.course.code} — {self.title} [{self.get_material_type_display()}]"


