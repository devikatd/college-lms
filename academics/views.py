"""
Academic entity management views, operational workstations, and REST API endpoints.
Provides complete lifecycle CRUD for:
- Departments, Degree Programs, Curriculum Schemes, Courses & Semesters, Batches
- Student Profiles & Faculty Academic Staff Directories
- Interactive Scheme Cloning Workstation
- Global Academic Data Retrieval & Search Engine
"""

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from accounts.models import User
from accounts.decorators import (
    role_required,
    college_admin_required,
    dept_admin_required,
    faculty_required,
)
from enrollment.models import (
    CourseOffering,
    StudentCourseEnrollment,
    AttendanceSession,
    StudentMark,
    TimetableEntry,
    CourseMaterial,
)
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
from .forms import (
    DepartmentForm,
    ProgramForm,
    SchemeForm,
    SchemeCloneForm,
    SemesterForm,
    CourseForm,
    BatchForm,
    StudentRegistrationForm,
    StudentEditForm,
    FacultyRegistrationForm,
    FacultyEditForm,
)
from .services import AcademicWorkflowService


# ── Visual Academic Hierarchy Explorer ───────────────────────────────────────

@login_required
def hierarchy_explorer_view(request):
    """
    Renders an interactive visual tree of the academic hierarchy:
    College -> Departments -> Programs -> Schemes -> Semesters -> Courses.
    """
    colleges = College.objects.prefetch_related(
        "departments__programs__schemes__semesters__courses"
    ).all()

    context = {
        "page_title": "Academic Hierarchy Explorer",
        "colleges": colleges,
    }
    return render(request, "academics/hierarchy_explorer.html", context)


# ── Department Management ───────────────────────────────────────────────────

@login_required
@dept_admin_required
def department_list_view(request):
    """List all departments (or scoped to user's assigned department)."""
    user = request.user
    if user.is_college_admin:
        departments = Department.objects.prefetch_related("programs", "faculty_members").annotate(
            prog_count=Count("programs", distinct=True),
            fac_count=Count("faculty_members", distinct=True),
        )
    else:
        dept = user.department
        departments = Department.objects.filter(pk=dept.pk) if dept else Department.objects.none()

    search_q = request.GET.get("q", "").strip()
    if search_q:
        departments = departments.filter(Q(name__icontains=search_q) | Q(code__icontains=search_q))

    context = {
        "page_title": "Academic Departments",
        "departments": departments,
        "search_q": search_q,
    }
    return render(request, "academics/department_list.html", context)


@login_required
@college_admin_required
def department_create_view(request):
    """Create a new academic department."""
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' [{dept.code}] created successfully.")
            return redirect("academics:department_detail", dept_id=dept.id)
    else:
        college = College.objects.first()
        form = DepartmentForm(initial={"college": college})

    context = {
        "page_title": "Add New Department",
        "form": form,
        "action": "Create",
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def department_edit_view(request, dept_id):
    """Edit existing department details."""
    dept = get_object_or_404(Department, pk=dept_id)
    if not request.user.is_college_admin and request.user.department != dept:
        messages.error(request, "Access Denied: You cannot edit other departments.")
        return redirect("academics:department_list")

    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, f"Department '{dept.code}' updated successfully.")
            return redirect("academics:department_detail", dept_id=dept.id)
    else:
        form = DepartmentForm(instance=dept)

    context = {
        "page_title": f"Edit Department: {dept.code}",
        "form": form,
        "action": "Update",
        "cancel_url": reverse("academics:department_detail", kwargs={"dept_id": dept.id}),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def department_detail_view(request, dept_id):
    """Comprehensive overview of a department showing its programs, batches, and faculty."""
    dept = get_object_or_404(Department.objects.prefetch_related("programs__schemes", "faculty_members__user"), pk=dept_id)

    if not request.user.is_college_admin and request.user.department != dept:
        messages.error(request, "Access Denied: You can only view your own department.")
        return redirect("portal:department_dashboard")

    programs = dept.programs.all()
    batches = Batch.objects.filter(program__department=dept).select_related("program", "scheme")
    faculty_list = dept.faculty_members.select_related("user").all()
    student_count = StudentProfile.objects.filter(batch__program__department=dept).count()

    context = {
        "page_title": f"Department: {dept.name}",
        "department": dept,
        "programs": programs,
        "batches": batches,
        "faculty_list": faculty_list,
        "student_count": student_count,
    }
    return render(request, "academics/department_detail.html", context)


# ── Degree Program Management ────────────────────────────────────────────────

@login_required
@dept_admin_required
def program_list_view(request):
    """List degree programs with department filter."""
    user = request.user
    programs = Program.objects.select_related("department").prefetch_related("schemes", "batches")

    if not user.is_college_admin:
        programs = programs.filter(department=user.department)

    dept_filter = request.GET.get("department")
    degree_filter = request.GET.get("degree_type")
    search_q = request.GET.get("q", "").strip()

    if dept_filter and user.is_college_admin:
        programs = programs.filter(department_id=dept_filter)
    if degree_filter:
        programs = programs.filter(degree_type=degree_filter)
    if search_q:
        programs = programs.filter(Q(name__icontains=search_q) | Q(code__icontains=search_q))

    departments = Department.objects.all() if user.is_college_admin else []

    context = {
        "page_title": "Degree Programs",
        "programs": programs,
        "departments": departments,
        "selected_dept": dept_filter,
        "selected_degree": degree_filter,
        "search_q": search_q,
    }
    return render(request, "academics/program_list.html", context)


@login_required
@dept_admin_required
def program_create_view(request):
    """Add a new degree program."""
    if request.method == "POST":
        form = ProgramForm(request.POST, user=request.user)
        if form.is_valid():
            prog = form.save()
            messages.success(request, f"Program '{prog.name}' [{prog.code}] created successfully.")
            return redirect("academics:program_detail", prog_id=prog.id)
    else:
        form = ProgramForm(user=request.user)

    context = {
        "page_title": "Add Degree Program",
        "form": form,
        "action": "Create",
        "cancel_url": reverse("academics:program_list"),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def program_edit_view(request, prog_id):
    """Edit degree program details."""
    prog = get_object_or_404(Program, pk=prog_id)
    if not request.user.is_college_admin and prog.department != request.user.department:
        messages.error(request, "Access Denied: You cannot modify programs outside your department.")
        return redirect("academics:program_list")

    if request.method == "POST":
        form = ProgramForm(request.POST, instance=prog, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Program '{prog.code}' updated successfully.")
            return redirect("academics:program_detail", prog_id=prog.id)
    else:
        form = ProgramForm(instance=prog, user=request.user)

    context = {
        "page_title": f"Edit Program: {prog.code}",
        "form": form,
        "action": "Update",
        "cancel_url": reverse("academics:program_detail", kwargs={"prog_id": prog.id}),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def program_detail_view(request, prog_id):
    """Program detail view showing curriculum schemes and student batches."""
    prog = get_object_or_404(Program.objects.select_related("department"), pk=prog_id)
    schemes = prog.schemes.prefetch_related("semesters__courses").all()
    batches = prog.batches.select_related("scheme").all()

    context = {
        "page_title": f"Program: {prog.name}",
        "program": prog,
        "schemes": schemes,
        "batches": batches,
    }
    return render(request, "academics/program_detail.html", context)


# ── Curriculum Scheme Management & Cloning Workstation ───────────────────────

@login_required
@dept_admin_required
def scheme_list_view(request):
    """List curriculum regulation schemes."""
    user = request.user
    schemes = Scheme.objects.select_related("program__department").prefetch_related("semesters__courses")

    if not user.is_college_admin:
        schemes = schemes.filter(program__department=user.department)

    search_q = request.GET.get("q", "").strip()
    if search_q:
        schemes = schemes.filter(Q(name__icontains=search_q) | Q(code__icontains=search_q))

    context = {
        "page_title": "Curriculum Schemes & Regulations",
        "schemes": schemes,
        "search_q": search_q,
    }
    return render(request, "academics/scheme_list.html", context)


@login_required
@dept_admin_required
def scheme_create_view(request):
    """Create a new curriculum scheme."""
    if request.method == "POST":
        form = SchemeForm(request.POST, user=request.user)
        if form.is_valid():
            scheme = form.save()
            # Auto-generate empty semesters based on program total_semesters
            for sem_num in range(1, scheme.program.total_semesters + 1):
                sem_type = Semester.SemesterType.ODD if sem_num % 2 == 1 else Semester.SemesterType.EVEN
                Semester.objects.get_or_create(scheme=scheme, semester_number=sem_num, defaults={"semester_type": sem_type})
            messages.success(request, f"Curriculum scheme '{scheme.code}' created with {scheme.program.total_semesters} default semesters.")
            return redirect("academics:scheme_detail", scheme_id=scheme.id)
    else:
        form = SchemeForm(user=request.user)

    context = {
        "page_title": "Add Curriculum Scheme",
        "form": form,
        "action": "Create",
        "cancel_url": reverse("academics:scheme_list"),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def scheme_clone_view(request):
    """
    Workstation UI exposing atomic scheme duplication.
    Clones all semesters and child courses into a new regulation scheme.
    """
    if request.method == "POST":
        form = SchemeCloneForm(request.POST, user=request.user)
        if form.is_valid():
            source_scheme = form.cleaned_data["source_scheme"]
            new_code = form.cleaned_data["new_code"].strip()
            new_name = form.cleaned_data["new_name"].strip()
            effective_year = form.cleaned_data["effective_year"]

            try:
                cloned = AcademicWorkflowService.clone_scheme(
                    source_scheme_id=source_scheme.id,
                    new_code=new_code,
                    new_name=new_name,
                    effective_year=effective_year,
                )
                messages.success(
                    request,
                    f"Curriculum Scheme successfully cloned! '{cloned.code}' ({cloned.name}) initialized with {cloned.semesters.count()} semesters."
                )
                return redirect("academics:scheme_detail", scheme_id=cloned.id)
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Failed to clone scheme: {str(e)}")
    else:
        source_id = request.GET.get("source_id")
        initial_data = {}
        if source_id:
            src = Scheme.objects.filter(pk=source_id).first()
            if src:
                initial_data = {
                    "source_scheme": src,
                    "new_code": f"{src.code}-CLONE",
                    "new_name": f"{src.name} (Revised)",
                    "effective_year": src.effective_year + 2,
                }
        form = SchemeCloneForm(initial=initial_data, user=request.user)

    context = {
        "page_title": "Curriculum Scheme Cloning Workstation",
        "form": form,
    }
    return render(request, "academics/scheme_clone.html", context)


@login_required
@dept_admin_required
def scheme_detail_view(request, scheme_id):
    """Detailed view of a scheme with all semesters and courses."""
    scheme = get_object_or_404(
        Scheme.objects.select_related("program__department").prefetch_related("semesters__courses"),
        pk=scheme_id,
    )
    semesters = scheme.semesters.order_by("semester_number")

    total_courses = sum(sem.courses.count() for sem in semesters)
    total_credits = sum(sum(c.credits for c in sem.courses.all()) for sem in semesters)

    context = {
        "page_title": f"Curriculum: {scheme.name} [{scheme.code}]",
        "scheme": scheme,
        "semesters": semesters,
        "total_courses": total_courses,
        "total_credits": total_credits,
    }
    return render(request, "academics/scheme_detail.html", context)


# ── Course & Semester Management ────────────────────────────────────────────

@login_required
@dept_admin_required
def course_list_view(request):
    """Comprehensive course directory with filters."""
    user = request.user
    courses = Course.objects.select_related("semester__scheme__program__department").order_by(
        "semester__scheme__code", "semester__semester_number", "code"
    )

    if not user.is_college_admin:
        courses = courses.filter(semester__scheme__program__department=user.department)

    search_q = request.GET.get("q", "").strip()
    type_filter = request.GET.get("course_type")
    scheme_filter = request.GET.get("scheme")

    if search_q:
        courses = courses.filter(Q(code__icontains=search_q) | Q(title__icontains=search_q) | Q(syllabus_summary__icontains=search_q))
    if type_filter:
        courses = courses.filter(course_type=type_filter)
    if scheme_filter:
        courses = courses.filter(semester__scheme_id=scheme_filter)

    schemes = Scheme.objects.filter(program__department=user.department) if user.is_dept_admin else Scheme.objects.all()

    context = {
        "page_title": "Course Directory & Syllabi",
        "courses": courses,
        "schemes": schemes,
        "search_q": search_q,
        "selected_type": type_filter,
        "selected_scheme": scheme_filter,
        "course_types": Course.CourseType.choices,
    }
    return render(request, "academics/course_list.html", context)


@login_required
@dept_admin_required
def course_create_view(request):
    """Add a new academic course to a semester."""
    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Course '{course.code} — {course.title}' created.")
            return redirect("academics:course_detail", course_id=course.id)
    else:
        initial = {}
        sem_id = request.GET.get("semester_id")
        if sem_id:
            initial["semester"] = sem_id
        form = CourseForm(initial=initial, user=request.user)

    context = {
        "page_title": "Add New Course",
        "form": form,
        "action": "Create",
        "cancel_url": reverse("academics:course_list"),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def course_edit_view(request, course_id):
    """Edit existing course syllabus and attributes."""
    course = get_object_or_404(Course, pk=course_id)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Course '{course.code}' updated.")
            return redirect("academics:course_detail", course_id=course.id)
    else:
        form = CourseForm(instance=course, user=request.user)

    context = {
        "page_title": f"Edit Course: {course.code}",
        "form": form,
        "action": "Update",
        "cancel_url": reverse("academics:course_detail", kwargs={"course_id": course.id}),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
def course_detail_view(request, course_id):
    """Detailed view of a course syllabus, L-T-P breakdown, and active offerings."""
    course = get_object_or_404(
        Course.objects.select_related("semester__scheme__program__department"),
        pk=course_id,
    )
    offerings = course.offerings.select_related("batch", "faculty__user").filter(is_active=True)

    context = {
        "page_title": f"{course.code} — {course.title}",
        "course": course,
        "offerings": offerings,
    }
    return render(request, "academics/course_detail.html", context)


# ── Student Batch Management ────────────────────────────────────────────────

@login_required
@dept_admin_required
def batch_list_view(request):
    """List batches / cohorts with active status and enrollment stats."""
    user = request.user
    batches = Batch.objects.select_related("program__department", "scheme").prefetch_related("students")

    if not user.is_college_admin:
        batches = batches.filter(program__department=user.department)

    search_q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status")

    if search_q:
        batches = batches.filter(Q(name__icontains=search_q) | Q(program__code__icontains=search_q))
    if status_filter == "graduated":
        batches = batches.filter(is_graduated=True)
    elif status_filter == "active":
        batches = batches.filter(is_graduated=False)

    context = {
        "page_title": "Student Batches & Cohorts",
        "batches": batches,
        "search_q": search_q,
        "status_filter": status_filter,
    }
    return render(request, "academics/batch_list.html", context)


@login_required
@dept_admin_required
def batch_create_view(request):
    """Create a new student batch."""
    if request.method == "POST":
        form = BatchForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                batch = form.save()
                messages.success(request, f"Batch '{batch.name}' created.")
                return redirect("academics:batch_detail", batch_id=batch.id)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = BatchForm(user=request.user)

    context = {
        "page_title": "Add Student Batch",
        "form": form,
        "action": "Create",
        "cancel_url": reverse("academics:batch_list"),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def batch_edit_view(request, batch_id):
    """Edit student batch details."""
    batch = get_object_or_404(Batch, pk=batch_id)
    if request.method == "POST":
        form = BatchForm(request.POST, instance=batch, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Batch '{batch.name}' updated.")
                return redirect("academics:batch_detail", batch_id=batch.id)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = BatchForm(instance=batch, user=request.user)

    context = {
        "page_title": f"Edit Batch: {batch.name}",
        "form": form,
        "action": "Update",
        "cancel_url": reverse("academics:batch_detail", kwargs={"batch_id": batch.id}),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def batch_detail_view(request, batch_id):
    """Batch detailed overview showing student roster, active offerings, and actions."""
    batch = get_object_or_404(
        Batch.objects.select_related("program__department", "scheme"),
        pk=batch_id,
    )
    students = batch.students.select_related("user").order_by("register_number")
    offerings = batch.course_offerings.select_related("course", "faculty__user").filter(is_active=True)

    context = {
        "page_title": f"Cohort: {batch.name}",
        "batch": batch,
        "students": students,
        "offerings": offerings,
    }
    return render(request, "academics/batch_detail.html", context)


# ── Student Information Management & Dossier ────────────────────────────────

@login_required
@dept_admin_required
def student_list_view(request):
    """Searchable student directory filterable by batch and academic standing."""
    user = request.user
    students = StudentProfile.objects.select_related("user", "batch__program__department").order_by("register_number")

    if not user.is_college_admin:
        students = students.filter(batch__program__department=user.department)

    search_q = request.GET.get("q", "").strip()
    batch_filter = request.GET.get("batch")
    status_filter = request.GET.get("status")

    if search_q:
        students = students.filter(
            Q(register_number__icontains=search_q)
            | Q(roll_number__icontains=search_q)
            | Q(user__first_name__icontains=search_q)
            | Q(user__last_name__icontains=search_q)
            | Q(user__email__icontains=search_q)
        )
    if batch_filter:
        students = students.filter(batch_id=batch_filter)
    if status_filter:
        students = students.filter(status=status_filter)

    batches = Batch.objects.filter(program__department=user.department) if user.is_dept_admin else Batch.objects.all()

    context = {
        "page_title": "Student Directory",
        "students": students,
        "batches": batches,
        "search_q": search_q,
        "selected_batch": batch_filter,
        "selected_status": status_filter,
        "status_choices": StudentProfile.StudentStatus.choices,
    }
    return render(request, "academics/student_list.html", context)


@login_required
@dept_admin_required
def student_create_view(request):
    """Create a new student with automatic User account creation."""
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                uname = form.cleaned_data["username"]
                pwd = form.cleaned_data["password"] or "pass123"
                user = User.objects.create_user(
                    username=uname,
                    email=form.cleaned_data["email"],
                    password=pwd,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    role=User.Role.STUDENT,
                )
                student = StudentProfile.objects.create(
                    user=user,
                    batch=form.cleaned_data["batch"],
                    register_number=form.cleaned_data["register_number"],
                    roll_number=form.cleaned_data["roll_number"],
                    status=form.cleaned_data["status"],
                    admission_date=form.cleaned_data["admission_date"],
                    emergency_contact=form.cleaned_data["emergency_contact"],
                    blood_group=form.cleaned_data["blood_group"],
                )
                messages.success(request, f"Student '{student.full_name}' ({student.register_number}) registered successfully with login username '{uname}'.")
                return redirect("academics:student_detail", student_id=student.id)
    else:
        form = StudentRegistrationForm(user=request.user)

    context = {
        "page_title": "Register New Student",
        "form": form,
        "action": "Register",
        "cancel_url": reverse("academics:student_list"),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def student_edit_view(request, student_id):
    """Edit student academic profile and user info."""
    student = get_object_or_404(StudentProfile.objects.select_related("user", "batch__program__department"), pk=student_id)

    if not request.user.is_college_admin and student.department != request.user.department:
        messages.error(request, "Access Denied: You cannot edit students outside your department.")
        return redirect("academics:student_list")

    if request.method == "POST":
        form = StudentEditForm(request.POST, instance=student, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                student = form.save()
                student.user.first_name = form.cleaned_data["first_name"]
                student.user.last_name = form.cleaned_data["last_name"]
                student.user.email = form.cleaned_data["email"]
                student.user.save()
                messages.success(request, f"Student profile for '{student.full_name}' updated.")
                return redirect("academics:student_detail", student_id=student.id)
    else:
        form = StudentEditForm(instance=student, user=request.user)

    context = {
        "page_title": f"Edit Student: {student.register_number}",
        "form": form,
        "action": "Update",
        "cancel_url": reverse("academics:student_detail", kwargs={"student_id": student.id}),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
def student_detail_view(request, student_id):
    """
    Comprehensive Academic Dossier for a student.
    Shows enrolled courses, attendance records, continuous internal marks, and curriculum progress.
    """
    student = get_object_or_404(
        StudentProfile.objects.select_related("user", "batch__program__department", "batch__scheme"),
        pk=student_id,
    )

    # Security: student can only view their own dossier; faculty/admins can view per permissions
    if request.user.is_student and getattr(request.user, "student_profile", None) != student:
        return HttpResponseForbidden("Access Denied: You can only view your own academic dossier.")

    enrollments = student.enrollments.select_related(
        "course_offering__course",
        "course_offering__faculty__user",
    ).prefetch_related("marks__component").all()

    total_credits = sum(enr.course_offering.course.credits for enr in enrollments)

    context = {
        "page_title": f"Academic Dossier: {student.full_name}",
        "student": student,
        "enrollments": enrollments,
        "total_credits": total_credits,
    }
    return render(request, "academics/student_detail.html", context)


# ── Faculty Academic Staff Directory & Management ───────────────────────────

@login_required
@dept_admin_required
def faculty_list_view(request):
    """Searchable directory of academic faculty and department staff."""
    user = request.user
    faculty_list = FacultyProfile.objects.select_related("user", "department").order_by("department", "user__last_name")

    if not user.is_college_admin:
        faculty_list = faculty_list.filter(department=user.department)

    search_q = request.GET.get("q", "").strip()
    dept_filter = request.GET.get("department")

    if search_q:
        faculty_list = faculty_list.filter(
            Q(employee_id__icontains=search_q)
            | Q(designation__icontains=search_q)
            | Q(user__first_name__icontains=search_q)
            | Q(user__last_name__icontains=search_q)
            | Q(user__email__icontains=search_q)
        )
    if dept_filter and user.is_college_admin:
        faculty_list = faculty_list.filter(department_id=dept_filter)

    departments = Department.objects.all() if user.is_college_admin else []

    context = {
        "page_title": "Faculty & Academic Staff",
        "faculty_list": faculty_list,
        "departments": departments,
        "search_q": search_q,
        "selected_dept": dept_filter,
    }
    return render(request, "academics/faculty_list.html", context)


@login_required
@dept_admin_required
def faculty_create_view(request):
    """Register a new faculty member with User account creation."""
    if request.method == "POST":
        form = FacultyRegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                uname = form.cleaned_data["username"]
                pwd = form.cleaned_data["password"] or "pass123"
                user = User.objects.create_user(
                    username=uname,
                    email=form.cleaned_data["email"],
                    password=pwd,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    role=User.Role.FACULTY,
                    is_staff=True,
                )
                faculty = FacultyProfile.objects.create(
                    user=user,
                    department=form.cleaned_data["department"],
                    employee_id=form.cleaned_data["employee_id"],
                    designation=form.cleaned_data["designation"],
                    qualification=form.cleaned_data["qualification"],
                    cabin_location=form.cleaned_data["cabin_location"],
                    joining_date=form.cleaned_data["joining_date"],
                )
                messages.success(request, f"Faculty '{faculty.full_name}' [{faculty.employee_id}] registered successfully.")
                return redirect("academics:faculty_detail", faculty_id=faculty.id)
    else:
        form = FacultyRegistrationForm(user=request.user)

    context = {
        "page_title": "Register Faculty Member",
        "form": form,
        "action": "Register",
        "cancel_url": reverse("academics:faculty_list"),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
@dept_admin_required
def faculty_edit_view(request, faculty_id):
    """Edit faculty profile attributes."""
    faculty = get_object_or_404(FacultyProfile.objects.select_related("user", "department"), pk=faculty_id)

    if not request.user.is_college_admin and faculty.department != request.user.department:
        messages.error(request, "Access Denied: You cannot edit faculty from other departments.")
        return redirect("academics:faculty_list")

    if request.method == "POST":
        form = FacultyEditForm(request.POST, instance=faculty, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                faculty = form.save()
                faculty.user.first_name = form.cleaned_data["first_name"]
                faculty.user.last_name = form.cleaned_data["last_name"]
                faculty.user.email = form.cleaned_data["email"]
                faculty.user.save()
                messages.success(request, f"Faculty profile for '{faculty.full_name}' updated.")
                return redirect("academics:faculty_detail", faculty_id=faculty.id)
    else:
        form = FacultyEditForm(instance=faculty, user=request.user)

    context = {
        "page_title": f"Edit Faculty: {faculty.full_name}",
        "form": form,
        "action": "Update",
        "cancel_url": reverse("academics:faculty_detail", kwargs={"faculty_id": faculty.id}),
    }
    return render(request, "academics/entity_form.html", context)


@login_required
def faculty_detail_view(request, faculty_id):
    """View faculty profile, assigned course offerings, and teaching schedule."""
    faculty = get_object_or_404(
        FacultyProfile.objects.select_related("user", "department"),
        pk=faculty_id,
    )
    assigned_offerings = faculty.assigned_offerings.select_related("course", "batch").filter(is_active=True)
    timetable_slots = TimetableEntry.objects.filter(course_offering__faculty=faculty).select_related(
        "course_offering__course"
    ).order_by("day_of_week", "slot_number")

    context = {
        "page_title": f"Faculty Profile: {faculty.full_name}",
        "faculty": faculty,
        "offerings": assigned_offerings,
        "timetable_slots": timetable_slots,
    }
    return render(request, "academics/faculty_detail.html", context)


# ── Global Academic Data Retrieval & Search Engine ───────────────────────────

@login_required
def global_search_view(request):
    """
    Centralized academic record finder.
    Directly resolves Problem Statement requirement:
    - Avoids difficulty in finding records
    - Cross-searches Students, Courses, Batches, Programs, and Faculty
    """
    q = request.GET.get("q", "").strip()
    user = request.user

    results = {
        "students": [],
        "courses": [],
        "batches": [],
        "programs": [],
        "faculty": [],
        "total_count": 0,
    }

    if q:
        # Students search
        stud_qs = StudentProfile.objects.select_related("user", "batch__program__department").filter(
            Q(register_number__icontains=q)
            | Q(roll_number__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
        )
        if user.is_dept_admin:
            stud_qs = stud_qs.filter(batch__program__department=user.department)
        results["students"] = list(stud_qs[:8])

        # Courses search
        course_qs = Course.objects.select_related("semester__scheme__program").filter(
            Q(code__icontains=q) | Q(title__icontains=q) | Q(syllabus_summary__icontains=q)
        )
        results["courses"] = list(course_qs[:8])

        # Batches search
        batch_qs = Batch.objects.select_related("program").filter(
            Q(name__icontains=q) | Q(program__code__icontains=q)
        )
        results["batches"] = list(batch_qs[:6])

        # Programs search
        prog_qs = Program.objects.select_related("department").filter(
            Q(name__icontains=q) | Q(code__icontains=q)
        )
        results["programs"] = list(prog_qs[:6])

        # Faculty search
        fac_qs = FacultyProfile.objects.select_related("user", "department").filter(
            Q(employee_id__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(designation__icontains=q)
        )
        results["faculty"] = list(fac_qs[:6])

        results["total_count"] = (
            len(results["students"])
            + len(results["courses"])
            + len(results["batches"])
            + len(results["programs"])
            + len(results["faculty"])
        )

    context = {
        "page_title": "Academic Record Finder & Search",
        "query": q,
        "results": results,
    }
    return render(request, "academics/global_search.html", context)


# ── Asynchronous Cascading Select API Endpoints ──────────────────────────────

@login_required
def api_departments(request, college_id):
    """Returns departments under a specific college."""
    departments = Department.objects.filter(college_id=college_id).values("id", "code", "name")
    return JsonResponse({"results": list(departments)})


@login_required
def api_programs(request, dept_id):
    """Returns programs offered by a specific department."""
    programs = Program.objects.filter(department_id=dept_id).values(
        "id", "code", "name", "degree_type", "duration_years", "total_semesters"
    )
    return JsonResponse({"results": list(programs)})


@login_required
def api_schemes(request, prog_id):
    """Returns curriculum schemes governing a specific degree program."""
    schemes = Scheme.objects.filter(program_id=prog_id).values(
        "id", "code", "name", "effective_year", "total_credits_required", "is_active"
    )
    return JsonResponse({"results": list(schemes)})


@login_required
def api_semesters(request, scheme_id):
    """Returns semesters defined under a specific regulation scheme."""
    semesters = Semester.objects.filter(scheme_id=scheme_id).order_by("semester_number").values(
        "id", "semester_number", "semester_type"
    )
    return JsonResponse({"results": list(semesters)})


@login_required
def api_courses(request, semester_id):
    """Returns courses taught in a specific semester."""
    courses = Course.objects.filter(semester_id=semester_id).order_by("code").values(
        "id", "code", "title", "course_type", "credits", "lecture_hours", "tutorial_hours", "practical_hours"
    )
    return JsonResponse({"results": list(courses)})
