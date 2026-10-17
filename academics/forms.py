"""
Forms for Academic entity management (Departments, Programs, Schemes, Semesters, Courses, Batches, Students, and Faculty).
"""

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User
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


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["college", "code", "name", "description"]
        widgets = {
            "college": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. CSE, ECE, MECH"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Department of Computer Science & Engineering"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Department overview, vision, or mission statement"}),
        }


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ["department", "code", "name", "degree_type", "duration_years", "total_semesters"]
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. BTECH-CS, MCA, MTECH-AI"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Bachelor of Technology in Computer Science"}),
            "degree_type": forms.Select(attrs={"class": "form-select"}),
            "duration_years": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 6}),
            "total_semesters": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 12}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["department"].queryset = Department.objects.filter(pk=user.department.pk)
            self.fields["department"].initial = user.department


class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = ["program", "code", "name", "effective_year", "total_credits_required", "is_active"]
        widgets = {
            "program": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. SCH2024, CBCS-2022"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 2024 Outcome-Based CBCS Curriculum"}),
            "effective_year": forms.NumberInput(attrs={"class": "form-input", "placeholder": "e.g. 2024"}),
            "total_credits_required": forms.NumberInput(attrs={"class": "form-input", "step": "0.5"}),
            "is_active": forms.CheckboxInput(attrs={"style": "width: 1.25rem; height: 1.25rem;"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["program"].queryset = Program.objects.filter(department=user.department)


class SchemeCloneForm(forms.Form):
    """Workstation form to clone an existing scheme, duplicating its semesters and courses."""
    source_scheme = forms.ModelChoiceField(
        queryset=Scheme.objects.select_related("program").all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Select base curriculum scheme to clone.",
    )
    new_code = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. SCH2026-CBCS"}),
        help_text="New unique scheme code.",
    )
    new_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 2026 Revised Autonomous Curriculum"}),
        help_text="Descriptive title for the cloned scheme.",
    )
    effective_year = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "2026"}),
        help_text="Applicable academic year.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["source_scheme"].queryset = Scheme.objects.filter(program__department=user.department)


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["scheme", "semester_number", "semester_type"]
        widgets = {
            "scheme": forms.Select(attrs={"class": "form-select"}),
            "semester_number": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 12}),
            "semester_type": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["scheme"].queryset = Scheme.objects.filter(program__department=user.department)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "semester",
            "code",
            "title",
            "course_type",
            "credits",
            "lecture_hours",
            "tutorial_hours",
            "practical_hours",
            "syllabus_summary",
        ]
        widgets = {
            "semester": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. CS301, MAT201"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Data Structures & Algorithms"}),
            "course_type": forms.Select(attrs={"class": "form-select"}),
            "credits": forms.NumberInput(attrs={"class": "form-input", "step": "0.5"}),
            "lecture_hours": forms.NumberInput(attrs={"class": "form-input", "min": 0, "max": 10}),
            "tutorial_hours": forms.NumberInput(attrs={"class": "form-input", "min": 0, "max": 10}),
            "practical_hours": forms.NumberInput(attrs={"class": "form-input", "min": 0, "max": 10}),
            "syllabus_summary": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Course outcomes, syllabus modules, reference textbooks"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["semester"].queryset = Semester.objects.filter(
                scheme__program__department=user.department
            ).select_related("scheme")


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ["program", "scheme", "name", "admission_year", "graduation_year", "current_semester", "is_graduated"]
        widgets = {
            "program": forms.Select(attrs={"class": "form-select"}),
            "scheme": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 2024-2028 CSE Batch A"}),
            "admission_year": forms.NumberInput(attrs={"class": "form-input", "placeholder": "2024"}),
            "graduation_year": forms.NumberInput(attrs={"class": "form-input", "placeholder": "2028"}),
            "current_semester": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 12}),
            "is_graduated": forms.CheckboxInput(attrs={"style": "width: 1.25rem; height: 1.25rem;"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["program"].queryset = Program.objects.filter(department=user.department)
            self.fields["scheme"].queryset = Scheme.objects.filter(program__department=user.department)


class StudentRegistrationForm(forms.Form):
    """Complete registration form creating both User and StudentProfile simultaneously."""
    # User fields
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Username (e.g. student_rahul)"}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "First Name"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Last Name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "email@rvce.edu.in"}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password (leave blank for default: pass123)"}))

    # StudentProfile fields
    batch = forms.ModelChoiceField(queryset=Batch.objects.select_related("program").all(), widget=forms.Select(attrs={"class": "form-select"}))
    register_number = forms.CharField(max_length=50, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "USN / Reg No (e.g. 1RV24CS050)"}))
    roll_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Class Roll No (e.g. CS-50)"}))
    status = forms.ChoiceField(choices=StudentProfile.StudentStatus.choices, initial=StudentProfile.StudentStatus.ACTIVE, widget=forms.Select(attrs={"class": "form-select"}))
    admission_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}))
    emergency_contact = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+91 9876543210"}))
    blood_group = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "O+, A+, B+"}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["batch"].queryset = Batch.objects.filter(program__department=user.department).select_related("program")

    def clean_username(self):
        uname = self.cleaned_data.get("username")
        if User.objects.filter(username=uname).exists():
            raise ValidationError(f"Username '{uname}' is already taken.")
        return uname

    def clean_register_number(self):
        reg = self.cleaned_data.get("register_number")
        if StudentProfile.objects.filter(register_number=reg).exists():
            raise ValidationError(f"Student with USN / Register Number '{reg}' already exists.")
        return reg


class StudentEditForm(forms.ModelForm):
    """Edit form for existing student profile."""
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-input"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-input"}))

    class Meta:
        model = StudentProfile
        fields = ["batch", "register_number", "roll_number", "status", "admission_date", "emergency_contact", "blood_group"]
        widgets = {
            "batch": forms.Select(attrs={"class": "form-select"}),
            "register_number": forms.TextInput(attrs={"class": "form-input"}),
            "roll_number": forms.TextInput(attrs={"class": "form-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "admission_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "emergency_contact": forms.TextInput(attrs={"class": "form-input"}),
            "blood_group": forms.TextInput(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
        if user and user.is_dept_admin and user.department:
            self.fields["batch"].queryset = Batch.objects.filter(program__department=user.department).select_related("program")


class FacultyRegistrationForm(forms.Form):
    """Registration form creating both User and FacultyProfile."""
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Username (e.g. dr_smith)"}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "First Name"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Last Name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "smith@rvce.edu.in"}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password (leave blank for default: pass123)"}))

    department = forms.ModelChoiceField(queryset=Department.objects.all(), widget=forms.Select(attrs={"class": "form-select"}))
    employee_id = forms.CharField(max_length=50, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "EMP-CS-105"}))
    designation = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Professor / Associate Professor"}))
    qualification = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ph.D. in Computer Science"}))
    cabin_location = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Admin Block Room 304"}))
    joining_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_dept_admin and user.department:
            self.fields["department"].queryset = Department.objects.filter(pk=user.department.pk)
            self.fields["department"].initial = user.department

    def clean_username(self):
        uname = self.cleaned_data.get("username")
        if User.objects.filter(username=uname).exists():
            raise ValidationError(f"Username '{uname}' is already taken.")
        return uname

    def clean_employee_id(self):
        emp_id = self.cleaned_data.get("employee_id")
        if FacultyProfile.objects.filter(employee_id=emp_id).exists():
            raise ValidationError(f"Employee ID '{emp_id}' is already registered.")
        return emp_id


class FacultyEditForm(forms.ModelForm):
    """Edit form for existing faculty profile."""
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-input"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-input"}))

    class Meta:
        model = FacultyProfile
        fields = ["department", "employee_id", "designation", "qualification", "cabin_location", "joining_date"]
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "employee_id": forms.TextInput(attrs={"class": "form-input"}),
            "designation": forms.TextInput(attrs={"class": "form-input"}),
            "qualification": forms.TextInput(attrs={"class": "form-input"}),
            "cabin_location": forms.TextInput(attrs={"class": "form-input"}),
            "joining_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
        if user and user.is_dept_admin and user.department:
            self.fields["department"].queryset = Department.objects.filter(pk=user.department.pk)
