from django.urls import path

from apps.branding.api.views import BrandingView

urlpatterns = [
    path("branding/", BrandingView.as_view(), name="branding"),
]
