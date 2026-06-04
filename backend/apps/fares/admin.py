from django.contrib import admin

from apps.fares.models import FareProduct, FareRule


class FareRuleInline(admin.TabularInline):
    model = FareRule
    extra = 0


@admin.register(FareProduct)
class FareProductAdmin(admin.ModelAdmin):
    list_display = ("name", "product_type", "status", "created_at")
    list_filter = ("product_type", "status")
    search_fields = ("name",)
    inlines = [FareRuleInline]


@admin.register(FareRule)
class FareRuleAdmin(admin.ModelAdmin):
    list_display = (
        "fare_product", "route", "origin_stop", "destination_stop",
        "calculation_method", "fixed_amount", "passenger_class", "priority",
    )
    list_filter = ("calculation_method", "passenger_class")
    search_fields = ("fare_product__name", "route__code")
