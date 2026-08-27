"""URL configuration for LiveTransmission."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "",
        TemplateView.as_view(template_name="home.html"),
        name="home",
    ),
    # HTML pages (apps will grow these in later stages)
    path("usuarios/", include("usuarios.urls")),
    path("transmissao/", include("transmissao.urls")),
    # REST API (ready for React later)
    path("api/usuarios/", include("usuarios.api_urls")),
    path("api/transmissao/", include("transmissao.api_urls")),
]
