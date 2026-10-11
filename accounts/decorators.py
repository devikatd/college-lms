"""
Role-Based Access Control (RBAC) decorators for view-level permission enforcement.

These decorators wrap Django views to restrict access based on the
authenticated user's role. They complement Django's built-in
@login_required decorator by adding granular role checks.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(allowed_roles):
    """
    Decorator that restricts view access to users with specific roles.

    Usage:
        @role_required(['COLLEGE_ADMIN', 'DEPT_ADMIN'])
        def manage_departments(request):
            ...

    Args:
        allowed_roles: List of role strings (matching User.Role choices)
                       that are permitted to access the decorated view.

    Behavior:
        - If the user is not authenticated, redirects to the login page.
        - If the user is authenticated but their role is not in
          `allowed_roles`, displays a 403-style warning message and
          redirects to their role-appropriate dashboard.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please log in to access this page.')
                return redirect('accounts:login')

            if request.user.role not in allowed_roles:
                messages.error(
                    request,
                    'Access Denied: You do not have permission to access this page.'
                )
                return redirect('accounts:login_redirect')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def college_admin_required(view_func):
    """
    Shorthand decorator: restricts access to College Administrators only.

    Usage:
        @college_admin_required
        def system_settings(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')

        if not request.user.is_college_admin:
            messages.error(
                request,
                'Access Denied: Only College Administrators can access this page.'
            )
            return redirect('accounts:login_redirect')

        return view_func(request, *args, **kwargs)
    return wrapper


def dept_admin_required(view_func):
    """
    Shorthand decorator: restricts access to Department Administrators
    and College Administrators (who have global scope).

    Usage:
        @dept_admin_required
        def manage_program(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')

        if not (request.user.is_college_admin or request.user.is_dept_admin):
            messages.error(
                request,
                'Access Denied: Only Department Administrators can access this page.'
            )
            return redirect('accounts:login_redirect')

        return view_func(request, *args, **kwargs)
    return wrapper


def faculty_required(view_func):
    """
    Shorthand decorator: restricts access to Faculty, Department Admins,
    and College Administrators.

    Usage:
        @faculty_required
        def view_course_roster(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')

        if not (request.user.is_college_admin or request.user.is_dept_admin or request.user.is_faculty):
            messages.error(
                request,
                'Access Denied: Only Academic Staff can access this page.'
            )
            return redirect('accounts:login_redirect')

        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    """
    Shorthand decorator: restricts access to Students only.

    Usage:
        @student_required
        def my_courses(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')

        if not request.user.is_student:
            messages.error(
                request,
                'Access Denied: This page is available to students only.'
            )
            return redirect('accounts:login_redirect')

        return view_func(request, *args, **kwargs)
    return wrapper


def department_scoped(view_func):
    """
    Ensures that if the user is a Department Administrator, they can only
    operate within their assigned department. College Administrators have
    global institution-wide access.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this page.')
            return redirect('accounts:login')

        if request.user.is_college_admin:
            return view_func(request, *args, **kwargs)

        if request.user.is_dept_admin:
            dept_id = kwargs.get('dept_id') or request.GET.get('dept_id') or request.POST.get('department')
            user_dept = request.user.department
            if dept_id and user_dept and str(user_dept.id) != str(dept_id) and str(user_dept.pk) != str(dept_id):
                messages.error(request, 'Access Denied: You cannot view or modify data outside your department.')
                return redirect('accounts:login_redirect')
            return view_func(request, *args, **kwargs)

        messages.error(request, 'Access Denied: Insufficient administrative privileges.')
        return redirect('accounts:login_redirect')
    return wrapper

