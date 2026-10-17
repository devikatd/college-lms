"""
URL configuration for the academics app.
"""

from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    # Visual Academic Hierarchy Explorer
    path("hierarchy/", views.hierarchy_explorer_view, name="hierarchy_explorer"),

    # Global Record Finder / Search Engine
    path("search/", views.global_search_view, name="global_search"),

    # Departments
    path("departments/", views.department_list_view, name="department_list"),
    path("departments/add/", views.department_create_view, name="department_create"),
    path("departments/<uuid:dept_id>/", views.department_detail_view, name="department_detail"),
    path("departments/<uuid:dept_id>/edit/", views.department_edit_view, name="department_edit"),

    # Degree Programs
    path("programs/", views.program_list_view, name="program_list"),
    path("programs/add/", views.program_create_view, name="program_create"),
    path("programs/<uuid:prog_id>/", views.program_detail_view, name="program_detail"),
    path("programs/<uuid:prog_id>/edit/", views.program_edit_view, name="program_edit"),

    # Curriculum Schemes & Cloning Workstation
    path("schemes/", views.scheme_list_view, name="scheme_list"),
    path("schemes/add/", views.scheme_create_view, name="scheme_create"),
    path("schemes/clone/", views.scheme_clone_view, name="scheme_clone"),
    path("schemes/<uuid:scheme_id>/", views.scheme_detail_view, name="scheme_detail"),

    # Courses & Syllabi
    path("courses/", views.course_list_view, name="course_list"),
    path("courses/add/", views.course_create_view, name="course_create"),
    path("courses/<uuid:course_id>/", views.course_detail_view, name="course_detail"),
    path("courses/<uuid:course_id>/edit/", views.course_edit_view, name="course_edit"),

    # Batches / Cohorts
    path("batches/", views.batch_list_view, name="batch_list"),
    path("batches/add/", views.batch_create_view, name="batch_create"),
    path("batches/<uuid:batch_id>/", views.batch_detail_view, name="batch_detail"),
    path("batches/<uuid:batch_id>/edit/", views.batch_edit_view, name="batch_edit"),
    path("batches/<uuid:batch_id>/csv-template/", views.download_student_csv_template_view, name="batch_csv_template"),
    path("batches/<uuid:batch_id>/upload-students/", views.batch_upload_students_csv_view, name="batch_upload_students"),

    # Students Directory & Profiles
    path("students/", views.student_list_view, name="student_list"),
    path("students/add/", views.student_create_view, name="student_create"),
    path("students/<uuid:student_id>/", views.student_detail_view, name="student_detail"),
    path("students/<uuid:student_id>/edit/", views.student_edit_view, name="student_edit"),
    path("students/<uuid:student_id>/transcript/", views.student_transcript_view, name="student_transcript"),


    # Faculty Directory & Profiles
    path("faculty/", views.faculty_list_view, name="faculty_list"),
    path("faculty/add/", views.faculty_create_view, name="faculty_create"),
    path("faculty/<uuid:faculty_id>/", views.faculty_detail_view, name="faculty_detail"),
    path("faculty/<uuid:faculty_id>/edit/", views.faculty_edit_view, name="faculty_edit"),

    # Cascading Dropdowns JSON APIs
    path("api/colleges/<uuid:college_id>/departments/", views.api_departments, name="api_departments"),
    path("api/departments/<uuid:dept_id>/programs/", views.api_programs, name="api_programs"),
    path("api/programs/<uuid:prog_id>/schemes/", views.api_schemes, name="api_schemes"),
    path("api/schemes/<uuid:scheme_id>/semesters/", views.api_semesters, name="api_semesters"),
    path("api/semesters/<uuid:semester_id>/courses/", views.api_courses, name="api_courses"),
]
