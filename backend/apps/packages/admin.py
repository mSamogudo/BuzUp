from django.contrib import admin

from apps.packages.models import Package, PackageRoute, PassengerPackage


class PackageRouteInline(admin.TabularInline):
    model = PackageRoute
    extra = 0


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "discount_type", "discount_value", "price", "validity_days", "max_trips", "status")
    list_filter = ("status", "discount_type")
    search_fields = ("name",)
    inlines = [PackageRouteInline]


@admin.register(PassengerPackage)
class PassengerPackageAdmin(admin.ModelAdmin):
    list_display = ("passenger_account", "package", "special_balance", "trips_used", "trips_remaining", "status", "expires_at")
    list_filter = ("status",)
    search_fields = ("passenger_account__full_name", "package__name")
