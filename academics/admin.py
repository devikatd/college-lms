"""
Administrative workstations and inline formsets for Academic domain models.

Provides hierarchical inlines:
- BatchInline inside ProgramAdmin
- SemesterInline inside SchemeAdmin
- CourseInline inside SemesterAdmin
Along with role-based scoping for Department Administrators and search/filtering.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
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


# ── Inline Formsets ──────────────────────────────────────────────────────────

class CourseInline(admin.TabularInline):
    model = Course
    extra = 1
    fields = ["code", "title", "course_type", "credits", "lecture_hours", "tutorial_hours", "practical_hours"]
    show_change_link = True


class SemesterInline(admin.TabularInline):
    model = Semester
    extra = 1
    fields = ["semester_number", "semester_type"]
    show_change_link = True
    ordering = ["semester_number"]


class BatchInline(admin.TabularInline):
    model = Batch
    extra = 0
    fields = ["name", "scheme", "admission_year", "graduation_year", "current_semester", "is_graduated"]
    show_change_link = True


# ── Model Admins ─────────────────────────────────────────────────────────────

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "established_year", "website", "department_count"]
    search_fields = ["code", "name"]
    ordering = ["name"]

    def department_count(self, obj):
        return obj.departments.count()
    department_count.short_description = "Departments"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "college", "program_count", "faculty_count"]
    list_filter = ["college"]
    search_fields = ["code", "name"]
    ordering = ["college", "code"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(pk=request.user.department.pk)
        return qs

    def program_count(self, obj):
        return obj.programs.count()
    program_count.short_description = "Programs"

    def faculty_count(self, obj):
        return obj.faculty_members.count()
    faculty_count.short_description = "Faculty"


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "department", "degree_type", "duration_years", "total_semesters", "batch_count"]
    list_filter = ["degree_type", "department__college", "department"]
    search_fields = ["code", "name", "department__name"]
    inlines = [BatchInline]
    ordering = ["department", "code"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(department=request.user.department)
        return qs

    def batch_count(self, obj):
        return obj.batches.count()
    batch_count.short_description = "Batches"


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "program", "effective_year", "total_credits_required", "is_active", "semester_count"]
    list_filter = ["is_active", "program__department", "effective_year"]
    search_fields = ["code", "name", "program__name"]
    inlines = [SemesterInline]
    ordering = ["program", "-effective_year"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(program__department=request.user.department)
        return qs

    def semester_count(self, obj):
        return obj.semesters.count()
    semester_count.short_description = "Semesters"


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ["scheme", "semester_number", "semester_type", "course_count"]
    list_filter = ["semester_type", "scheme__program__department"]
    search_fields = ["scheme__code", "scheme__name"]
    inlines = [CourseInline]
    ordering = ["scheme", "semester_number"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(scheme__program__department=request.user.department)
        return qs

    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = "Courses"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "get_program", "get_semester", "course_type", "credits", "ltp_notation"]
    list_filter = ["course_type", "semester__scheme__program__department", "semester__semester_number"]
    search_fields = ["code", "title", "syllabus_summary"]
    ordering = ["semester__scheme", "semester__semester_number", "code"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("semester__scheme__program__department")
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(semester__scheme__program__department=request.user.department)
        return qs

    def get_program(self, obj):
        return obj.semester.scheme.program.code
    get_program.short_description = "Program"

    def get_semester(self, obj):
        return f"Sem {obj.semester.semester_number}"
    get_semester.short_description = "Semester"

    def ltp_notation(self, obj):
        return format_html('<span style="font-family:monospace; font-weight:600;">{}</span>', obj.ltp_structure)
    ltp_notation.short_description = "L-T-P"


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ["name", "program", "scheme", "admission_year", "graduation_year", "current_semester", "status_badge", "student_count_badge"]
    list_filter = ["program__department", "admission_year", "is_graduated"]
    search_fields = ["name", "program__name", "scheme__name"]
    ordering = ["program", "-admission_year"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("program__department", "scheme")
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(program__department=request.user.department)
        return qs

    def status_badge(self, obj):
        if obj.is_graduated:
            return format_html('<span style="background-color: #64748b; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px;">Graduated</span>')
        return format_html('<span style="background-color: #10b981; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px;">Active</span>')
    status_badge.short_description = "Status"

    def student_count_badge(self, obj):
        count = obj.students.count()
        return format_html('<span style="background-color: #6366f1; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{} Students</span>', count)
    student_count_badge.short_description = "Enrolled Students"


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ["employee_id", "get_name", "department", "designation", "get_email", "joining_date"]
    list_filter = ["department", "designation"]
    search_fields = ["employee_id", "user__first_name", "user__last_name", "user__email", "designation"]
    ordering = ["department", "user__last_name"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("user", "department")
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(department=request.user.department)
        return qs

    def get_name(self, obj):
        return obj.full_name
    get_name.short_description = "Name"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["register_number", "roll_number", "get_name", "get_program", "batch", "status", "get_email"]
    list_filter = ["status", "batch__program__department", "batch__program", "batch__admission_year"]
    search_fields = ["register_number", "roll_number", "user__first_name", "user__last_name", "user__email"]
    ordering = ["batch", "register_number"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("user", "batch__program__department")
        if not request.user.is_superuser and request.user.is_dept_admin and request.user.department:
            return qs.filter(batch__program__department=request.user.department)
        return qs

    def get_name(self, obj):
        return obj.full_name
    get_name.short_description = "Full Name"

    def get_program(self, obj):
        return obj.program.code
    get_program.short_description = "Program"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
