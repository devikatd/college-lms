"""
URL configuration for the portal app.
"""

from django.urls import path

from . import views

app_name = 'portal'

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('department/', views.department_dashboard, name='department_dashboard'),
    path('faculty/', views.faculty_portal, name='faculty_portal'),
    path('student/', views.student_portal, name='student_portal'),
    path('analytics/attendance-alerts/', views.attendance_alerts_view, name='attendance_alerts'),
]
