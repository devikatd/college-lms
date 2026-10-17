"""
Forms for the portal application: Academic notices and campus circulars.
"""

from django import forms
from .models import AcademicNotice
from academics.models import Department


class AcademicNoticeForm(forms.ModelForm):
    """Form for creating and editing campus notices and circulars."""

    class Meta:
        model = AcademicNotice
        fields = [
            "title",
            "category",
            "priority",
            "target_role",
            "department",
            "content",
            "attachment_url",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g., Final Semester Exam Timetable Announcement",
            }),
            "category": forms.Select(attrs={"class": "form-input"}),
            "priority": forms.Select(attrs={"class": "form-input"}),
            "target_role": forms.Select(attrs={"class": "form-input"}),
            "department": forms.Select(attrs={"class": "form-input"}),
            "content": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 6,
                "placeholder": "Enter detailed announcement content, schedule details, or institutional guidelines...",
            }),
            "attachment_url": forms.URLInput(attrs={
                "class": "form-input",
                "placeholder": "https://example.edu/documents/circular-2026.pdf",
            }),
            "is_active": forms.CheckboxInput(attrs={"style": "width: auto;"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            if not self.user.is_college_admin and self.user.department:
                # Restrict department selection to admin's own department
                self.fields["department"].queryset = Department.objects.filter(id=self.user.department.id)
                self.fields["department"].initial = self.user.department
                self.fields["department"].empty_label = None
            else:
                self.fields["department"].empty_label = "Institution-Wide (All Departments)"
