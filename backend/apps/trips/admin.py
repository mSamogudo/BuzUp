from django.contrib import admin

from apps.trips.models import Driver, Trip, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("registration", "make", "model_name", "seated_capacity", "standing_capacity", "status")
    list_filter = ("status",)
    search_fields = ("registration", "make")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "license_number", "status")
    list_filter = ("status",)
    search_fields = ("full_name", "phone", "license_number")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("route", "vehicle", "driver", "planned_departure_at", "status")
    list_filter = ("status", "route")
    search_fields = ("route__code", "route__name")
