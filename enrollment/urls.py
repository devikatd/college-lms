"""
URL configuration for the enrollment, attendance, and assessment workstations.
"""

from django.urls import path
from . import views

app_name = "enrollment"

urlpatterns = [
    # Batch progression
    path("batch/<uuid:batch_id>/promote/", views.batch_promotion_view, name="batch_promote"),

    # Automated course offering generation
    path("offerings/generate/", views.generate_offerings_view, name="generate_offerings"),

    # Class roster CSV export
    path("offering/<uuid:offering_id>/roster.csv", views.export_roster_csv, name="export_roster_csv"),

    # Attendance management
    path("offering/<uuid:offering_id>/attendance/mark/", views.mark_attendance_view, name="mark_attendance"),
    path("offering/<uuid:offering_id>/attendance/history/", views.attendance_history_view, name="attendance_history"),

    # Assessment & marks management
    path("offering/<uuid:offering_id>/assessments/", views.manage_assessments_view, name="manage_assessments"),
    path("assessment/<uuid:component_id>/marks/", views.enter_marks_view, name="enter_marks"),

    # Final Course Letter Grade Evaluation
    path("offering/<uuid:offering_id>/grades/", views.enter_course_grades_view, name="enter_grades"),
]

