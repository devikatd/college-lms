"""
Portal views — role-specific dashboards with live academic telemetry.

Renders rich operational data for each user role:
- College Admin: Institution-wide statistics, department directories, and cohort overviews.
- Department Admin: Department-scoped programs, batches, faculty rosters, and student metrics.
- Faculty Portal: Assigned courses, classroom sections, and enrolled student rosters.
- Student Portal: Enrolled subjects, attendance percentage, credits, and full curriculum roadmap.
"""

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from accounts.models import User
from accounts.decorators import (
    role_required,
    college_admin_required,
    dept_admin_required,
    faculty_required,
    student_required,
)
from academics.models import (
    College,
    Department,
    Program,
    Scheme,
    Course,
    Batch,
    FacultyProfile,
    StudentProfile,
)
from enrollment.models import (
    CourseOffering,
    StudentCourseEnrollment,
    TimetableEntry,
    CourseMaterial,
)


@login_required
@college_admin_required
def admin_dashboard(request):
    """College Administrator executive dashboard with institutional KPI metrics."""
    context = {
        "page_title": "College Admin Dashboard",
        "user": request.user,
        "college": College.objects.first(),
        "department_count": Department.objects.count(),
        "program_count": Program.objects.count(),
        "scheme_count": Scheme.objects.count(),
        "course_count": Course.objects.count(),
        "batch_count": Batch.objects.count(),
        "faculty_count": FacultyProfile.objects.count(),
        "student_count": StudentProfile.objects.count(),
        "offerings_count": CourseOffering.objects.count(),
        "recent_batches": Batch.objects.select_related("program", "scheme").order_by("-admission_year")[:5],
        "departments": Department.objects.prefetch_related("programs", "faculty_members").all()[:6],
    }
    return render(request, "portal/admin_dashboard.html", context)


@login_required
@dept_admin_required
def department_dashboard(request):
    """Department Administrator operations dashboard scoped to user's assigned department."""
    dept = request.user.department

    if not dept and request.user.is_college_admin:
        dept = Department.objects.first()

    programs = dept.programs.all() if dept else []
    batches = Batch.objects.filter(program__department=dept).select_related("program", "scheme") if dept else []
    faculty_members = dept.faculty_members.select_related("user").all() if dept else []
    students_count = StudentProfile.objects.filter(batch__program__department=dept).count() if dept else 0
    courses_count = Course.objects.filter(semester__scheme__program__department=dept).distinct().count() if dept else 0

    context = {
        "page_title": "Department Dashboard",
        "user": request.user,
        "department": dept,
        "programs": programs,
        "batches": batches,
        "faculty_members": faculty_members,
        "students_count": students_count,
        "courses_count": courses_count,
    }
    return render(request, "portal/department_dashboard.html", context)


@login_required
@faculty_required
def faculty_portal(request):
    """Faculty teaching portal displaying assigned course offerings, students, and timetable schedule."""
    faculty_profile = getattr(request.user, "faculty_profile", None)

    offerings = []
    timetable_entries = []
    if faculty_profile:
        offerings = faculty_profile.assigned_offerings.select_related("course", "batch").prefetch_related(
            "enrollments__student__user",
            "materials",
        ).filter(is_active=True)
        timetable_entries = TimetableEntry.objects.filter(
            course_offering__faculty=faculty_profile,
            course_offering__is_active=True,
        ).select_related("course_offering__course", "course_offering__batch").order_by("day_of_week", "slot_number")

    context = {
        "page_title": "Faculty Portal",
        "user": request.user,
        "faculty_profile": faculty_profile,
        "offerings": offerings,
        "timetable_entries": timetable_entries,
    }
    return render(request, "portal/faculty_portal.html", context)


@login_required
@student_required
def student_portal(request):
    """Student academic portal showing current enrollments, timetable, and learning materials."""
    student_profile = getattr(request.user, "student_profile", None)

    enrollments = []
    curriculum_semesters = []
    timetable_entries = []
    learning_materials = []
    total_enrolled_credits = Decimal("0.00")

    if student_profile:
        enrollments = student_profile.enrollments.select_related(
            "course_offering__course",
            "course_offering__faculty__user",
            "course_offering__batch",
        ).prefetch_related("marks__component").all()

        offering_ids = [e.course_offering_id for e in enrollments]

        for enr in enrollments:
            total_enrolled_credits += enr.course_offering.course.credits

        if student_profile.batch and student_profile.batch.scheme:
            curriculum_semesters = student_profile.batch.scheme.semesters.prefetch_related(
                "courses"
            ).order_by("semester_number").all()

        timetable_entries = TimetableEntry.objects.filter(
            course_offering_id__in=offering_ids
        ).select_related("course_offering__course", "course_offering__faculty__user").order_by("day_of_week", "slot_number")

        learning_materials = CourseMaterial.objects.filter(
            course_offering_id__in=offering_ids
        ).select_related("course_offering__course", "course_offering__faculty__user").order_by("-uploaded_at")

    context = {
        "page_title": "Student Portal",
        "user": request.user,
        "student_profile": student_profile,
        "enrollments": enrollments,
        "total_enrolled_credits": total_enrolled_credits,
        "curriculum_semesters": curriculum_semesters,
        "timetable_entries": timetable_entries,
        "learning_materials": learning_materials,
    }
    return render(request, "portal/student_portal.html", context)


@login_required
@role_required([User.Role.COLLEGE_ADMIN, User.Role.DEPT_ADMIN])
def attendance_alerts_view(request):
    """Institutional Attendance Analytics & Exam Ineligibility (<75% shortage) Monitoring."""
    user = request.user
    selected_dept_id = request.GET.get("department")
    filter_status = request.GET.get("status", "all")
    search_q = request.GET.get("q", "").strip()

    enrollments_qs = StudentCourseEnrollment.objects.select_related(
        "student__user",
        "student__batch__program__department",
        "course_offering__course",
        "course_offering__faculty__user",
        "course_offering__batch",
    )

    if user.is_dept_admin:
        dept = user.department
        if dept:
            enrollments_qs = enrollments_qs.filter(course_offering__batch__program__department=dept)
    elif selected_dept_id:
        enrollments_qs = enrollments_qs.filter(course_offering__batch__program__department_id=selected_dept_id)

    if search_q:
        enrollments_qs = enrollments_qs.filter(
            Q(student__register_number__icontains=search_q)
            | Q(student__user__first_name__icontains=search_q)
            | Q(student__user__last_name__icontains=search_q)
            | Q(course_offering__course__code__icontains=search_q)
            | Q(course_offering__course__title__icontains=search_q)
        )

    # Calculate KPI aggregates before status filtering
    total_records = enrollments_qs.count()
    critical_records = enrollments_qs.filter(attendance_percentage__lt=Decimal("75.00")).count()
    warning_records = enrollments_qs.filter(attendance_percentage__gte=Decimal("75.00"), attendance_percentage__lt=Decimal("80.00")).count()
    satisfactory_records = enrollments_qs.filter(attendance_percentage__gte=Decimal("80.00")).count()

    # Apply status filter
    if filter_status == "critical":
        enrollments_qs = enrollments_qs.filter(attendance_percentage__lt=Decimal("75.00"))
    elif filter_status == "warning":
        enrollments_qs = enrollments_qs.filter(attendance_percentage__gte=Decimal("75.00"), attendance_percentage__lt=Decimal("80.00"))
    elif filter_status == "satisfactory":
        enrollments_qs = enrollments_qs.filter(attendance_percentage__gte=Decimal("80.00"))

    departments = Department.objects.all() if user.is_college_admin else []

    context = {
        "page_title": "Attendance Shortage & Exam Ineligibility Alerts",
        "user": user,
        "enrollments": enrollments_qs.order_by("attendance_percentage", "student__register_number"),
        "total_records": total_records,
        "critical_records": critical_records,
        "warning_records": warning_records,
        "satisfactory_records": satisfactory_records,
        "departments": departments,
        "selected_dept_id": selected_dept_id,
        "filter_status": filter_status,
        "search_q": search_q,
    }
    return render(request, "portal/attendance_alerts.html", context)

