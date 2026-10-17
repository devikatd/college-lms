from django.contrib import admin
from .models import AcademicNotice


@admin.register(AcademicNotice)
class AcademicNoticeAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "priority", "target_role", "department", "is_active", "created_at"]
    list_filter = ["category", "priority", "target_role", "is_active", "department"]
    search_fields = ["title", "content"]
    ordering = ["-created_at"]
