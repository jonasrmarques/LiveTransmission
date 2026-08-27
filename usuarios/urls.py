"""HTML page URL routes for usuarios (templates)."""

from django.urls import path

from usuarios import views

app_name = "usuarios"

urlpatterns = [
    path("cadastro/", views.cadastro_page, name="cadastro"),
    path("login/", views.login_page, name="login"),
    path("perfil/", views.perfil_page, name="perfil"),
]
