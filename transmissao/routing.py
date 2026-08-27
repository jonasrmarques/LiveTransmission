"""WebSocket URL routing for transmissao."""

from django.urls import path

from transmissao.consumers import SalaConsumer

websocket_urlpatterns = [
    path(
        "ws/transmissao/sala/<uuid:identificador>/",
        SalaConsumer.as_asgi(),
        name="ws-transmissao-sala",
    ),
]
