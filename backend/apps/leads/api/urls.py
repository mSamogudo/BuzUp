from django.urls import path

from apps.leads.api.views import ContactLeadCreateView

urlpatterns = [
    path("public/contact/", ContactLeadCreateView.as_view(), name="public-contact-lead"),
]
