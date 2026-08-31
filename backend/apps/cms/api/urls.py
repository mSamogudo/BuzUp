from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.cms.api.public import (
    PublicEcoSystemsView,
    PublicPageView,
    PublicPlansView,
    PublicSiteView,
)
from apps.cms.api.views import (
    EcoSystemViewSet,
    MediaViewSet,
    MenuViewSet,
    PageBlockViewSet,
    PageViewSet,
    PlanFeatureView,
    PlanViewSet,
    ScheduleViewSet,
    SeoView,
    VersionViewSet,
)

router = DefaultRouter()
router.register("cms/pages", PageViewSet, basename="cms-pages")
router.register("cms/blocks", PageBlockViewSet, basename="cms-blocks")
router.register("cms/versions", VersionViewSet, basename="cms-versions")
router.register("cms/media", MediaViewSet, basename="cms-media")
router.register("cms/menus", MenuViewSet, basename="cms-menus")
router.register("cms/plans", PlanViewSet, basename="cms-plans")
router.register("cms/eco-systems", EcoSystemViewSet, basename="cms-eco-systems")
router.register("cms/schedules", ScheduleViewSet, basename="cms-schedules")

urlpatterns = [
    path("cms/seo/<int:page_id>/", SeoView.as_view(), name="cms-seo"),
    path("cms/plan-features/", PlanFeatureView.as_view(), name="cms-plan-features"),

    # Entrega ao site publico (sem autenticacao, com cache).
    path("public/site/<str:locale>/", PublicSiteView.as_view(), name="public-site"),
    path("public/plans/<str:locale>/", PublicPlansView.as_view(), name="public-plans"),
    path("public/eco-systems/", PublicEcoSystemsView.as_view(), name="public-eco-systems"),
    # A pagina inicial tem slug vazio: entra pela rota curta.
    path("public/pages/<slug:locale>/", PublicPageView.as_view(), name="public-page-home"),
    path("public/pages/<path:slug>/<str:locale>/", PublicPageView.as_view(), name="public-page"),

    path("", include(router.urls)),
]
