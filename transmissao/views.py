"""HTML page views for the transmissao domain."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from transmissao.room_access import (
    SalaAccessDeniedError,
    SalaNotFoundError,
    ensure_room_access,
    get_sala_by_identificador,
)


@login_required(login_url="usuarios:login")
@require_http_methods(["GET"])
def criar_sala_page(request):
    return render(request, "transmissao/criar_sala.html")


@login_required(login_url="usuarios:login")
@require_http_methods(["GET"])
def entrar_sala_page(request):
    codigo = request.GET.get("codigo", "")
    return render(request, "transmissao/entrar_sala.html", {"codigo": codigo})


@login_required(login_url="usuarios:login")
@require_http_methods(["GET"])
def sala_page(request, identificador):
    try:
        sala = get_sala_by_identificador(identificador)
        ensure_room_access(sala, request.user)
    except SalaNotFoundError:
        return redirect("transmissao:entrar")
    except SalaAccessDeniedError:
        return redirect("transmissao:entrar")

    return render(
        request,
        "transmissao/sala.html",
        {
            "sala_identificador": str(sala.identificador),
            "current_user_id": request.user.id,
        },
    )
