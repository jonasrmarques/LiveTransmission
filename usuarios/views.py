"""HTML page views for the usuarios domain."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def cadastro_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "usuarios/cadastro.html")


@require_http_methods(["GET"])
def login_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "usuarios/login.html")


@login_required(login_url="usuarios:login")
@require_http_methods(["GET"])
def perfil_page(request):
    return render(request, "usuarios/perfil.html")
