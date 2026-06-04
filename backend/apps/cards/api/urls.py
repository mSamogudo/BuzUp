from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.cards.api.views import (
    CardActivateView,
    CardAssignView,
    CardBlockView,
    CardLookupView,
    CardQrPngView,
    CardReplaceView,
    CardViewSet,
)

router = DefaultRouter()
router.register("cards", CardViewSet, basename="cards")

urlpatterns = [
    path("card-actions/lookup/", CardLookupView.as_view(), name="card-lookup"),
    path("card-actions/activate/", CardActivateView.as_view(), name="card-activate"),
    path("card-actions/block/", CardBlockView.as_view(), name="card-block"),
    path("card-actions/assign/", CardAssignView.as_view(), name="card-assign"),
    path("card-actions/replace/", CardReplaceView.as_view(), name="card-replace"),
    path("cards/<int:card_id>/qr.png", CardQrPngView.as_view(), name="card-qr-png"),
    path("", include(router.urls)),
]
