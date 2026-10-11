"""
Root URL configuration for the lms_core project.

Routes all traffic through the modular app URL configurations:
- /accounts/  → Authentication (login, logout, redirect)
- /portal/    → Role-specific dashboards
- /academics/ → Academic management (Phase 2+)
- /enrollment/→ Course offerings & enrollments (Phase 2+)
- /admin/     → Django admin back-office
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def root_redirect(request):
    """Redirect root URL to login or dashboard."""
    if request.user.is_authenticated:
        return redirect('accounts:login_redirect')
    return redirect('accounts:login')


urlpatterns = [
    # Root redirect
    path('', root_redirect, name='root'),

    # Django admin back-office
    path('admin/', admin.site.urls),

    # App routes
    path('accounts/', include('accounts.urls')),
    path('portal/', include('portal.urls')),
    path('academics/', include('academics.urls')),
    path('enrollment/', include('enrollment.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
