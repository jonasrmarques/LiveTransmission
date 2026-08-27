"""REST API URL routes for usuarios (/api/usuarios/)."""

from django.urls import path

from usuarios.api_views import (
    CadastroAPIView,
    LoginAPIView,
    LogoutAPIView,
    PerfilAPIView,
)

urlpatterns = [
    path("cadastro/", CadastroAPIView.as_view(), name="api-usuarios-cadastro"),
    path("login/", LoginAPIView.as_view(), name="api-usuarios-login"),
    path("logout/", LogoutAPIView.as_view(), name="api-usuarios-logout"),
    path("perfil/", PerfilAPIView.as_view(), name="api-usuarios-perfil"),
]
