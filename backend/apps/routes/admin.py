from django.contrib import admin

from apps.routes.models import Route, RouteStop, Stop


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    ordering = ("direction", "sequence")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "name")
    inlines = [RouteStopInline]


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "latitude", "longitude", "status")
    list_filter = ("status",)
    search_fields = ("code", "name")
