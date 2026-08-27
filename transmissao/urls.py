"""HTML page URL routes for transmissao (templates)."""

from django.urls import path

from transmissao import views

app_name = "transmissao"

urlpatterns = [
    path("criar/", views.criar_sala_page, name="criar"),
    path("entrar/", views.entrar_sala_page, name="entrar"),
    path("sala/<uuid:identificador>/", views.sala_page, name="sala"),
]
