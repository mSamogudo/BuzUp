from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.passengers.api.extract import PassengerExtractView
from apps.passengers.api.views import PassengerAccountViewSet

router = DefaultRouter()
router.register("passengers", PassengerAccountViewSet, basename="passengers")

urlpatterns = [
    path("passengers/<int:pk>/extract/", PassengerExtractView.as_view(), name="passenger-extract"),
    path("", include(router.urls)),
]
