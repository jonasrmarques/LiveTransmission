"""Serializers for the transmissao domain."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from transmissao.models import ParticipanteSala, Sala

User = get_user_model()


class ParticipanteSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(source="usuario.id", read_only=True)
    username = serializers.CharField(source="usuario.username", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ParticipanteSala
        fields = (
            "id",
            "usuario_id",
            "username",
            "is_owner",
            "ativo",
            "joined_at",
            "left_at",
        )
        read_only_fields = fields

    def get_is_owner(self, obj: ParticipanteSala) -> bool:
        return obj.usuario_id == obj.sala.proprietario_id


class SalaSerializer(serializers.ModelSerializer):
    proprietario_id = serializers.IntegerField(source="proprietario.id", read_only=True)
    proprietario_username = serializers.CharField(
        source="proprietario.username",
        read_only=True,
    )
    is_owner = serializers.SerializerMethodField()
    participantes = serializers.SerializerMethodField()
    convite_url = serializers.SerializerMethodField()

    class Meta:
        model = Sala
        fields = (
            "id",
            "identificador",
            "nome",
            "codigo_convite",
            "status",
            "proprietario_id",
            "proprietario_username",
            "is_owner",
            "participantes",
            "convite_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_owner(self, obj: Sala) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.proprietario_id == request.user.id

    def get_participantes(self, obj: Sala):
        participantes = obj.participantes.filter(ativo=True).select_related("usuario")
        return ParticipanteSerializer(participantes, many=True).data

    def get_convite_url(self, obj: Sala) -> str:
        request = self.context.get("request")
        if not request:
            return f"/transmissao/entrar/?codigo={obj.codigo_convite}"
        return request.build_absolute_uri(
            f"/transmissao/entrar/?codigo={obj.codigo_convite}"
        )


class SalaCreateSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=120)

    def validate_nome(self, value: str) -> str:
        nome = value.strip()
        if not nome:
            raise serializers.ValidationError("Informe um nome para a sala.")
        return nome


class EntrarPorCodigoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=16)

    def validate_codigo(self, value: str) -> str:
        return value.strip().upper()
