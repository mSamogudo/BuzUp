from django.urls import path

from apps.sms.api.views import TripBroadcastView

urlpatterns = [
    path("admin/broadcasts/", TripBroadcastView.as_view(), name="sms-broadcast"),
]
