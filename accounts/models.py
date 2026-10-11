"""
Custom User model with role-based access control.

Extends Django's AbstractUser to add a `role` field that determines
which dashboard and permissions a user receives upon authentication.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for the College LMS.

    Each user is assigned exactly one role that governs their access level:
    - COLLEGE_ADMIN: Full institution-wide access to all departments and data.
    - DEPT_ADMIN: Scoped access to their assigned department's programs, schemes, batches, and students.
    - FACULTY: Access to their assigned course offerings and enrolled student rosters.
    - STUDENT: Read-only access to their own academic profile, enrolled courses, and curriculum.
    """

    class Role(models.TextChoices):
        COLLEGE_ADMIN = 'COLLEGE_ADMIN', 'College Administrator'
        DEPT_ADMIN = 'DEPT_ADMIN', 'Department Administrator'
        FACULTY = 'FACULTY', 'Academic Staff / Faculty'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text='Determines the user\'s access level and dashboard view.',
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text='Contact phone number.',
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text='Optional profile photograph.',
    )
    assigned_department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dept_admins',
        help_text='Assigned department for Department Administrators.',
    )

    # ── Role convenience properties ──────────────────────────────────

    @property
    def is_college_admin(self):
        """Returns True if the user is a College Administrator."""
        return self.role == self.Role.COLLEGE_ADMIN

    @property
    def is_dept_admin(self):
        """Returns True if the user is a Department Administrator."""
        return self.role == self.Role.DEPT_ADMIN

    @property
    def is_faculty(self):
        """Returns True if the user is Academic Staff / Faculty."""
        return self.role == self.Role.FACULTY

    @property
    def is_student(self):
        """Returns True if the user is a Student."""
        return self.role == self.Role.STUDENT

    @property
    def role_display(self):
        """Returns the human-readable role label."""
        return self.get_role_display()

    @property
    def department(self):
        """Returns the user's affiliated Department instance based on their role."""
        if self.is_dept_admin:
            return self.assigned_department
        if self.is_faculty and hasattr(self, 'faculty_profile'):
            return self.faculty_profile.department
        if self.is_student and hasattr(self, 'student_profile'):
            return self.student_profile.department
        return self.assigned_department

    # ── Dashboard URL routing ────────────────────────────────────────

    @property
    def dashboard_url(self):
        """Returns the URL name for this user's role-specific dashboard."""
        from django.urls import reverse
        role_url_map = {
            self.Role.COLLEGE_ADMIN: 'portal:admin_dashboard',
            self.Role.DEPT_ADMIN: 'portal:department_dashboard',
            self.Role.FACULTY: 'portal:faculty_portal',
            self.Role.STUDENT: 'portal:student_portal',
        }
        url_name = role_url_map.get(self.role, 'portal:student_portal')
        return reverse(url_name)

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.role_display})'

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']
