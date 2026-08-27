from django.contrib import admin

from transmissao.models import ParticipanteSala, Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nome", "proprietario", "codigo_convite", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("nome", "codigo_convite", "proprietario__username")
    readonly_fields = ("identificador", "codigo_convite", "created_at", "updated_at")


@admin.register(ParticipanteSala)
class ParticipanteSalaAdmin(admin.ModelAdmin):
    list_display = ("sala", "usuario", "ativo", "joined_at", "left_at")
    list_filter = ("ativo",)
    search_fields = ("sala__nome", "usuario__username")
