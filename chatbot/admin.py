from django.contrib import admin
from .models import ContraceptiveMethod

@admin.register(ContraceptiveMethod)
class ContraceptiveMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "effectiveness", "side_effects", "suitability")
    search_fields = ("name", "description")