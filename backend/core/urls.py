"""
ESG Analytics Platform — Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static


def health_check(request):
    return JsonResponse({"message": "Backend API working", "status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("", health_check),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)