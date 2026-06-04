from django.contrib import admin

from apps.cards.models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "card_type", "card_technology", "status", "passenger_account", "created_at")
    list_filter = ("card_type", "status", "card_technology", "issued_batch")
    search_fields = ("card_uid", "card_number", "passenger_account__full_name")
