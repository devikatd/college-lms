"""
URL configuration for the academics app.
"""

from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    # Visual Academic Hierarchy Explorer
    path("hierarchy/", views.hierarchy_explorer_view, name="hierarchy_explorer"),

    # Cascading Dropdowns JSON APIs
    path("api/colleges/<uuid:college_id>/departments/", views.api_departments, name="api_departments"),
    path("api/departments/<uuid:dept_id>/programs/", views.api_programs, name="api_programs"),
    path("api/programs/<uuid:prog_id>/schemes/", views.api_schemes, name="api_schemes"),
    path("api/schemes/<uuid:scheme_id>/semesters/", views.api_semesters, name="api_semesters"),
    path("api/semesters/<uuid:semester_id>/courses/", views.api_courses, name="api_courses"),
]
