"""REST API views for the transmissao domain."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from transmissao.models import Sala
from transmissao.permissions import IsRoomOwner, IsRoomParticipant
from transmissao.serializers import (
    EntrarPorCodigoSerializer,
    SalaCreateSerializer,
    SalaSerializer,
)
from transmissao.room_access import get_sala_by_identificador
from transmissao.services import (
    SalaAccessDeniedError,
    SalaClosedError,
    SalaNotFoundError,
    SalaServiceError,
    ParticipanteNotFoundError,
    create_sala,
    end_transmission,
    join_sala,
    join_sala_by_code,
    leave_sala,
    list_user_salas,
    remove_participant,
    start_transmission,
)

User = get_user_model()


def _serialize_sala(sala, request):
    return SalaSerializer(sala, context={"request": request}).data


def _service_error_response(exc: SalaServiceError):
    if isinstance(exc, SalaNotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, (SalaAccessDeniedError, ParticipanteNotFoundError)):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, SalaClosedError):
        code = status.HTTP_400_BAD_REQUEST
    else:
        code = status.HTTP_400_BAD_REQUEST
    return Response({"detail": str(exc)}, status=code)


class SalaListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        salas = list_user_salas(request.user)
        data = SalaSerializer(salas, many=True, context={"request": request}).data
        return Response(data)

    def post(self, request):
        serializer = SalaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sala = create_sala(owner=request.user, nome=serializer.validated_data["nome"])
        return Response(
            _serialize_sala(sala, request),
            status=status.HTTP_201_CREATED,
        )


class SalaDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoomParticipant]

    def get_object(self, identificador):
        sala = get_sala_by_identificador(identificador)
        self.check_object_permissions(self.request, sala)
        return sala

    def get(self, request, identificador):
        try:
            sala = self.get_object(identificador)
        except SalaNotFoundError as exc:
            return _service_error_response(exc)
        return Response(_serialize_sala(sala, request))


class EntrarPorCodigoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EntrarPorCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sala = join_sala_by_code(
                codigo=serializer.validated_data["codigo"],
                user=request.user,
            )
        except SalaServiceError as exc:
            return _service_error_response(exc)
        return Response(_serialize_sala(sala, request))


class SalaEntrarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, identificador):
        try:
            sala = get_sala_by_identificador(identificador)
            join_sala(sala=sala, user=request.user)
        except SalaServiceError as exc:
            return _service_error_response(exc)
        return Response(_serialize_sala(sala, request))


class SalaSairAPIView(APIView):
    # Only auth: after encerrar everyone is inactive, so IsRoomParticipant
    # would 403 guests who still click "Sair". leave_sala is idempotent.
    permission_classes = [IsAuthenticated]

    def post(self, request, identificador):
        try:
            sala = get_sala_by_identificador(identificador)
            leave_sala(sala=sala, user=request.user)
        except SalaServiceError as exc:
            return _service_error_response(exc)
        return Response({"detail": "Você saiu da sala."})


class SalaIniciarAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoomOwner]

    def post(self, request, identificador):
        try:
            sala = get_sala_by_identificador(identificador)
            self.check_object_permissions(request, sala)
            sala = start_transmission(sala=sala, owner=request.user)
        except SalaServiceError as exc:
            return _service_error_response(exc)
        return Response(_serialize_sala(sala, request))


class SalaEncerrarAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoomOwner]

    def post(self, request, identificador):
        try:
            sala = get_sala_by_identificador(identificador)
            self.check_object_permissions(request, sala)
            sala = end_transmission(sala=sala, owner=request.user)
        except SalaServiceError as exc:
            return _service_error_response(exc)
        return Response(_serialize_sala(sala, request))


class SalaRemoverParticipanteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoomOwner]

    def delete(self, request, identificador, user_id):
        try:
            sala = get_sala_by_identificador(identificador)
            self.check_object_permissions(request, sala)
            participant = get_object_or_404(User, pk=user_id)
            remove_participant(sala=sala, owner=request.user, participant=participant)
        except SalaServiceError as exc:
            return _service_error_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
