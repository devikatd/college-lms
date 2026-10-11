"""
Authentication views for the College LMS.

Handles login, logout, and post-login role-based redirect dispatching.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LMSLoginForm


def login_view(request):
    """
    Renders the login page and authenticates users.
    On successful login, redirects to the role-based redirect dispatcher.
    """
    # If already authenticated, send to dashboard
    if request.user.is_authenticated:
        return redirect('accounts:login_redirect')

    if request.method == 'POST':
        form = LMSLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            # Check for 'next' parameter
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:login_redirect')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = LMSLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Logs out the current user and redirects to the login page.
    """
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


@login_required
def login_redirect_view(request):
    """
    Post-login redirect dispatcher.

    Routes each authenticated user to their role-appropriate dashboard:
    - COLLEGE_ADMIN  → /portal/admin/
    - DEPT_ADMIN     → /portal/department/
    - FACULTY        → /portal/faculty/
    - STUDENT        → /portal/student/
    """
    user = request.user

    if user.is_college_admin:
        return redirect('portal:admin_dashboard')
    elif user.is_dept_admin:
        return redirect('portal:department_dashboard')
    elif user.is_faculty:
        return redirect('portal:faculty_portal')
    elif user.is_student:
        return redirect('portal:student_portal')
    else:
        # Fallback for any edge case
        messages.warning(request, 'Your account does not have an assigned role. Please contact the administrator.')
        return redirect('accounts:login')
