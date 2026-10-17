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

    # Campus Notice Board & Circulars
    path('notices/', views.notice_list_view, name='notice_list'),
    path('notices/create/', views.notice_create_view, name='notice_create'),
    path('notices/<uuid:notice_id>/', views.notice_detail_view, name='notice_detail'),
    path('notices/<uuid:notice_id>/delete/', views.notice_delete_view, name='notice_delete'),
]

