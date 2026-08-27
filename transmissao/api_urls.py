"""REST API URL routes for transmissao (/api/transmissao/)."""

from django.urls import path

from transmissao.api_views import (
    EntrarPorCodigoAPIView,
    SalaDetailAPIView,
    SalaEncerrarAPIView,
    SalaEntrarAPIView,
    SalaIniciarAPIView,
    SalaListCreateAPIView,
    SalaRemoverParticipanteAPIView,
    SalaSairAPIView,
)

urlpatterns = [
    path("salas/", SalaListCreateAPIView.as_view(), name="api-transmissao-salas"),
    path(
        "salas/entrar/",
        EntrarPorCodigoAPIView.as_view(),
        name="api-transmissao-salas-entrar-codigo",
    ),
    path(
        "salas/<uuid:identificador>/",
        SalaDetailAPIView.as_view(),
        name="api-transmissao-sala-detail",
    ),
    path(
        "salas/<uuid:identificador>/entrar/",
        SalaEntrarAPIView.as_view(),
        name="api-transmissao-sala-entrar",
    ),
    path(
        "salas/<uuid:identificador>/sair/",
        SalaSairAPIView.as_view(),
        name="api-transmissao-sala-sair",
    ),
    path(
        "salas/<uuid:identificador>/iniciar/",
        SalaIniciarAPIView.as_view(),
        name="api-transmissao-sala-iniciar",
    ),
    path(
        "salas/<uuid:identificador>/encerrar/",
        SalaEncerrarAPIView.as_view(),
        name="api-transmissao-sala-encerrar",
    ),
    path(
        "salas/<uuid:identificador>/participantes/<int:user_id>/",
        SalaRemoverParticipanteAPIView.as_view(),
        name="api-transmissao-sala-remover-participante",
    ),
]
