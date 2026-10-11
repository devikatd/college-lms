"""
Views and JSON API endpoints for Academic hierarchy exploration and dynamic cascading dropdowns.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from .models import College, Department, Program, Scheme, Semester, Course


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
