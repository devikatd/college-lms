"""
Admin configuration for enrollment, attendance, and assessment operational entities.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CourseOffering,
    StudentCourseEnrollment,
    AttendanceSession,
    AttendanceRecord,
    AssessmentComponent,
    StudentMark,
    TimetableEntry,
    CourseMaterial,
)


class StudentCourseEnrollmentInline(admin.TabularInline):
    model = StudentCourseEnrollment
    extra = 0
    fields = ["student", "status", "attendance_percentage", "grade", "enrolled_on"]
    readonly_fields = ["enrolled_on"]
    show_change_link = True


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ["student", "is_present", "remarks"]
    show_change_link = True


class StudentMarkInline(admin.TabularInline):
    model = StudentMark
    extra = 0
    fields = ["enrollment", "marks_obtained"]
    show_change_link = True


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ["course", "batch", "faculty", "academic_year", "term", "section", "is_active", "enrolled_count"]
    list_filter = ["academic_year", "term", "is_active", "batch__program__department"]
    search_fields = ["course__code", "course__title", "batch__name", "faculty__user__first_name", "faculty__user__last_name"]
    inlines = [StudentCourseEnrollmentInline]
    ordering = ["-academic_year", "term", "course__code"]

    def enrolled_count(self, obj):
        count = obj.enrollments.count()
        return format_html('<span style="background-color: #0284c7; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px;">{} Students</span>', count)
    enrolled_count.short_description = "Enrollments"


@admin.register(StudentCourseEnrollment)
class StudentCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["get_student_usn", "get_student_name", "get_course", "course_offering", "status", "attendance_percentage", "grade"]
    list_filter = ["status", "course_offering__academic_year", "course_offering__term", "course_offering__batch__program"]
    search_fields = ["student__register_number", "student__user__first_name", "student__user__last_name", "course_offering__course__code"]
    ordering = ["student__register_number"]

    def get_student_usn(self, obj):
        return obj.student.register_number
    get_student_usn.short_description = "USN / Reg No"

    def get_student_name(self, obj):
        return obj.student.full_name
    get_student_name.short_description = "Student"

    def get_course(self, obj):
        return obj.course_offering.course.code
    get_course.short_description = "Course"


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ["course_offering", "date", "slot", "topic_covered", "present_count_badge"]
    list_filter = ["course_offering__academic_year", "course_offering__term", "date"]
    search_fields = ["course_offering__course__code", "topic_covered"]
    inlines = [AttendanceRecordInline]
    ordering = ["-date", "-slot"]

    def present_count_badge(self, obj):
        present = obj.records.filter(is_present=True).count()
        total = obj.records.count()
        return format_html('<span style="background-color: #10b981; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px;">{}/{} Present</span>', present, total)
    present_count_badge.short_description = "Attendance"


@admin.register(AssessmentComponent)
class AssessmentComponentAdmin(admin.ModelAdmin):
    list_display = ["course_offering", "name", "max_marks", "weightage_percentage", "conducted_date"]
    list_filter = ["course_offering__academic_year", "course_offering__term"]
    search_fields = ["course_offering__course__code", "name"]
    inlines = [StudentMarkInline]
    ordering = ["course_offering", "name"]


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ["day_of_week", "slot_number", "course_offering", "start_time", "end_time", "classroom"]
    list_filter = ["day_of_week", "classroom", "course_offering__academic_year"]
    search_fields = ["course_offering__course__code", "classroom", "course_offering__faculty__user__first_name"]
    ordering = ["day_of_week", "slot_number"]


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ["course_offering", "title", "material_type", "uploaded_at"]
    list_filter = ["material_type", "course_offering__academic_year"]
    search_fields = ["title", "course_offering__course__code", "description"]
    ordering = ["-uploaded_at"]

