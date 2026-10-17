"""
Portal operational models: Institutional Academic Notices & Circulars.
"""

import uuid
from django.conf import settings
from django.db import models


class AcademicNotice(models.Model):
    """
    Campus academic announcement and notice board circular.
    Supports targeting by role (All, Faculty, Students) and department scoping.
    """

    class Category(models.TextChoices):
        CIRCULAR = "CIRCULAR", "Academic Circular"
        EXAM = "EXAM", "Examinations & Evaluation"
        TIMETABLE = "TIMETABLE", "Timetable & Classes"
        EVENT = "EVENT", "Seminar & Campus Events"
        URGENT = "URGENT", "Urgent Advisory"

    class Priority(models.TextChoices):
        NORMAL = "NORMAL", "Standard"
        IMPORTANT = "IMPORTANT", "Important"
        CRITICAL = "CRITICAL", "High Priority / Critical"

    class TargetRole(models.TextChoices):
        ALL = "ALL", "Institution-Wide (All Users)"
        FACULTY = "FACULTY", "Faculty & Academic Staff"
        STUDENT = "STUDENT", "Enrolled Students"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, help_text="Announcement headline.")
    content = models.TextField(help_text="Full text / circular body.")
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.CIRCULAR,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    target_role = models.CharField(
        max_length=20,
        choices=TargetRole.choices,
        default=TargetRole.ALL,
    )
    department = models.ForeignKey(
        "academics.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notices",
        help_text="Target department. Leave blank for institution-wide circular.",
    )
    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="published_notices",
    )
    attachment_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional external link or reference document URL.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Academic Notice"
        verbose_name_plural = "Academic Notices"
        ordering = ["-created_at"]

    def __str__(self):
        dept_str = f" [{self.department.code}]" if self.department else " [All Campus]"
        return f"[{self.get_category_display()}]{dept_str} {self.title}"
