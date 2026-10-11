"""
Enrollment, operational offerings, promotion, and roster export views.
"""

import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError

from accounts.decorators import dept_admin_required, faculty_required
from academics.models import Batch, Department, FacultyProfile, Course
from academics.services import AcademicWorkflowService
from .models import (
    CourseOffering,
    StudentCourseEnrollment,
    AttendanceSession,
    AttendanceRecord,
    AssessmentComponent,
    StudentMark,
)


@login_required
@dept_admin_required
def batch_promotion_view(request, batch_id):
    """
    Action view to promote a batch to the next academic semester or mark graduation.
    """
    batch = get_object_or_404(Batch.objects.select_related("program__department", "scheme"), pk=batch_id)

    # Department scoping check
    if not request.user.is_college_admin and request.user.is_dept_admin:
        if batch.program.department != request.user.department:
            messages.error(request, "Access Denied: You cannot modify batches outside your department.")
            return redirect("portal:department_dashboard")

    if request.method == "POST":
        try:
            result = AcademicWorkflowService.promote_batch(batch.id)
            messages.success(request, result["message"])
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect("portal:department_dashboard")

    context = {
        "page_title": f"Promote Batch: {batch.name}",
        "batch": batch,
        "current_semester": batch.current_semester,
        "max_semesters": batch.program.total_semesters,
        "is_final_semester": batch.current_semester >= batch.program.total_semesters,
    }
    return render(request, "enrollment/batch_promotion.html", context)


@login_required
@dept_admin_required
def generate_offerings_view(request):
    """
    Automated course offering generation workstation for Department Administrators.
    Selects batch and academic term, pulling courses from the curriculum scheme.
    """
    dept = request.user.department
    if not dept and request.user.is_college_admin:
        dept = Department.objects.first()

    batches = Batch.objects.filter(program__department=dept, is_graduated=False).select_related("program", "scheme")
    faculty_list = FacultyProfile.objects.filter(department=dept).select_related("user")

    selected_batch_id = request.GET.get("batch_id")
    selected_batch = None
    preview_courses = []

    if selected_batch_id:
        selected_batch = batches.filter(id=selected_batch_id).first()
        if selected_batch:
            current_sem = selected_batch.scheme.semesters.filter(
                semester_number=selected_batch.current_semester
            ).first()
            if current_sem:
                preview_courses = current_sem.courses.all()

    if request.method == "POST":
        batch_id = request.POST.get("batch_id")
        academic_year = request.POST.get("academic_year")
        term = request.POST.get("term")
        section = request.POST.get("section", "A")

        target_batch = get_object_or_404(Batch, id=batch_id)

        # Faculty allocation mapping from POST
        faculty_map = {}
        for key, val in request.POST.items():
            if key.startswith("faculty_") and val:
                course_code = key.replace("faculty_", "")
                faculty_prof = FacultyProfile.objects.filter(id=val).first()
                if faculty_prof:
                    faculty_map[course_code] = faculty_prof

        try:
            offerings = AcademicWorkflowService.generate_course_offerings_for_batch(
                batch_id=target_batch.id,
                academic_year=academic_year,
                term=term,
                section=section,
                default_faculty_map=faculty_map,
            )
            messages.success(
                request,
                f"Successfully initialized {len(offerings)} course offerings for {target_batch.name} ({academic_year} {term} Term)."
            )

            # Auto-enroll students if checkbox was selected
            if request.POST.get("auto_enroll"):
                enrolled_count = AcademicWorkflowService.bulk_enroll_batch_students(
                    batch_id=target_batch.id,
                    academic_year=academic_year,
                    term=term,
                    section=section,
                )
                messages.info(request, f"Bulk registered {enrolled_count} student course enrollments.")

            return redirect("portal:department_dashboard")
        except ValidationError as e:
            messages.error(request, str(e))

    context = {
        "page_title": "Generate Course Offerings",
        "batches": batches,
        "selected_batch": selected_batch,
        "preview_courses": preview_courses,
        "faculty_list": faculty_list,
    }
    return render(request, "enrollment/generate_offerings.html", context)


@login_required
@faculty_required
def export_roster_csv(request, offering_id):
    """
    Exports a clean CSV file of students enrolled in the given course offering.
    Accessible to the assigned Faculty instructor, Department Admin, and College Admin.
    """
    offering = get_object_or_404(
        CourseOffering.objects.select_related("course", "batch", "faculty__user"),
        pk=offering_id,
    )

    # Security check: ensure instructor belongs to offering unless admin
    if request.user.is_faculty and not (request.user.is_college_admin or request.user.is_dept_admin):
        if not offering.faculty or offering.faculty.user != request.user:
            return HttpResponseForbidden("Access Denied: You are not the assigned instructor for this course.")

    # CSV streaming response
    response = HttpResponse(content_type="text/csv")
    filename = f"Roster_{offering.course.code}_{offering.academic_year}_{offering.term}_Sec{offering.section}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "USN / Register Number",
        "Student Name",
        "Class Roll No",
        "Email",
        "Course Code",
        "Course Title",
        "Section",
        "Attendance (%)",
        "Status",
        "Grade",
    ])

    enrollments = offering.enrollments.select_related("student__user").order_by("student__register_number")
    for enr in enrollments:
        student = enr.student
        writer.writerow([
            student.register_number,
            student.full_name,
            student.roll_number,
            student.user.email,
            offering.course.code,
            offering.course.title,
            offering.section,
            f"{enr.attendance_percentage}%",
            enr.get_status_display(),
            enr.grade or "Pending",
        ])

    return response


# ── Attendance Management Workstations ───────────────────────────────────────

@login_required
@faculty_required
def mark_attendance_view(request, offering_id):
    """
    Classroom attendance marking interface for faculty.
    Presents the roster of enrolled students with one-click toggles and updates cumulative attendance.
    """
    import datetime
    from decimal import Decimal

    offering = get_object_or_404(
        CourseOffering.objects.select_related("course", "batch", "faculty__user"),
        pk=offering_id,
    )

    if request.user.is_faculty and not (request.user.is_college_admin or request.user.is_dept_admin):
        if not offering.faculty or offering.faculty.user != request.user:
            return HttpResponseForbidden("Access Denied: You are not assigned to this course offering.")

    enrollments = offering.enrollments.select_related("student__user").order_by("student__register_number")

    if request.method == "POST":
        date_str = request.POST.get("date")
        slot = int(request.POST.get("slot", 1))
        topic_covered = request.POST.get("topic_covered", "").strip()

        try:
            session_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
        except ValueError:
            session_date = datetime.date.today()

        session, _ = AttendanceSession.objects.get_or_create(
            course_offering=offering,
            date=session_date,
            slot=slot,
            defaults={"topic_covered": topic_covered},
        )
        if topic_covered and session.topic_covered != topic_covered:
            session.topic_covered = topic_covered
            session.save(update_fields=["topic_covered"])

        # Record presence for each student
        for enr in enrollments:
            student = enr.student
            is_present = f"present_{student.id}" in request.POST
            remarks = request.POST.get(f"remarks_{student.id}", "").strip()

            AttendanceRecord.objects.update_or_create(
                session=session,
                student=student,
                defaults={"is_present": is_present, "remarks": remarks},
            )

        # Recalculate cumulative attendance percentages for all enrolled students
        total_sessions = offering.attendance_sessions.count()
        if total_sessions > 0:
            for enr in enrollments:
                present_count = AttendanceRecord.objects.filter(
                    session__course_offering=offering,
                    student=enr.student,
                    is_present=True,
                ).count()
                pct = round(Decimal(present_count) / Decimal(total_sessions) * 100, 2)
                enr.attendance_percentage = pct
                enr.save(update_fields=["attendance_percentage"])

        messages.success(
            request,
            f"Attendance recorded for {session_date} (Slot {slot}). Updated {enrollments.count()} student records."
        )
        return redirect("enrollment:attendance_history", offering_id=offering.id)

    context = {
        "page_title": f"Take Attendance — {offering.course.code}",
        "offering": offering,
        "enrollments": enrollments,
        "today": datetime.date.today().isoformat(),
    }
    return render(request, "enrollment/mark_attendance.html", context)


@login_required
@faculty_required
def attendance_history_view(request, offering_id):
    """Displays chronological attendance sessions and presence logs for an offering."""
    offering = get_object_or_404(
        CourseOffering.objects.select_related("course", "batch", "faculty__user"),
        pk=offering_id,
    )
    sessions = offering.attendance_sessions.prefetch_related("records__student__user").all()

    context = {
        "page_title": f"Attendance Ledger — {offering.course.code}",
        "offering": offering,
        "sessions": sessions,
    }
    return render(request, "enrollment/attendance_history.html", context)


# ── Assessment & Marks Workstations ──────────────────────────────────────────

@login_required
@faculty_required
def manage_assessments_view(request, offering_id):
    """
    List and create Continuous Internal Evaluation (CIE) components.
    """
    offering = get_object_or_404(
        CourseOffering.objects.select_related("course", "batch", "faculty__user"),
        pk=offering_id,
    )

    if request.user.is_faculty and not (request.user.is_college_admin or request.user.is_dept_admin):
        if not offering.faculty or offering.faculty.user != request.user:
            return HttpResponseForbidden("Access Denied: You are not assigned to this course offering.")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        max_marks = request.POST.get("max_marks", 50.0)
        weightage = request.POST.get("weightage_percentage", 20.0)
        conducted_date = request.POST.get("conducted_date") or None

        if name:
            AssessmentComponent.objects.get_or_create(
                course_offering=offering,
                name=name,
                defaults={
                    "max_marks": max_marks,
                    "weightage_percentage": weightage,
                    "conducted_date": conducted_date,
                },
            )
            messages.success(request, f"Assessment component '{name}' configured.")
            return redirect("enrollment:manage_assessments", offering_id=offering.id)

    components = offering.assessment_components.prefetch_related("marks").all()
    context = {
        "page_title": f"Assessments & Marks — {offering.course.code}",
        "offering": offering,
        "components": components,
    }
    return render(request, "enrollment/manage_assessments.html", context)


@login_required
@faculty_required
def enter_marks_view(request, component_id):
    """
    Spreadsheet-style marks entry view for a specific CIE component.
    """
    from decimal import Decimal

    component = get_object_or_404(
        AssessmentComponent.objects.select_related("course_offering__course", "course_offering__batch", "course_offering__faculty__user"),
        pk=component_id,
    )
    offering = component.course_offering

    if request.user.is_faculty and not (request.user.is_college_admin or request.user.is_dept_admin):
        if not offering.faculty or offering.faculty.user != request.user:
            return HttpResponseForbidden("Access Denied: You are not assigned to this course offering.")

    enrollments = offering.enrollments.select_related("student__user").order_by("student__register_number")
    existing_marks = {m.enrollment_id: m.marks_obtained for m in component.marks.all()}

    if request.method == "POST":
        updated_count = 0
        for enr in enrollments:
            val = request.POST.get(f"mark_{enr.id}")
            if val is not None and val != "":
                try:
                    score = Decimal(val)
                    if 0 <= score <= component.max_marks:
                        StudentMark.objects.update_or_create(
                            component=component,
                            enrollment=enr,
                            defaults={"marks_obtained": score},
                        )
                        updated_count += 1
                    else:
                        messages.warning(
                            request,
                            f"Score {score} for {enr.student.register_number} exceeds max marks ({component.max_marks}). Skipped."
                        )
                except Exception:
                    pass

        messages.success(request, f"Successfully recorded marks for {updated_count} students.")
        return redirect("enrollment:manage_assessments", offering_id=offering.id)

    context = {
        "page_title": f"Enter Marks: {component.name}",
        "component": component,
        "offering": offering,
        "enrollments": enrollments,
        "existing_marks": existing_marks,
    }
    return render(request, "enrollment/enter_marks.html", context)

