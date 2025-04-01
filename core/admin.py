from django.contrib import admin
from .models import MokkBaseJSON


@admin.register(MokkBaseJSON)
class MokkBaseJSONAdmin(admin.ModelAdmin):
    list_display = ('path', 'created_at', 'updated_at', 'creator')