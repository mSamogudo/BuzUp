from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.site_header = "BuzUp"
admin.site.site_title = "BuzUp Admin"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.users.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
