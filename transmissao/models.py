"""Domain models for private transmission rooms."""

import secrets
import uuid

from django.conf import settings
from django.db import models


def generate_invite_code() -> str:
    """Generate a short, URL-safe invite code."""
    return secrets.token_urlsafe(6).upper().replace("-", "")[:8]


class Sala(models.Model):
    class Status(models.TextChoices):
        AGUARDANDO = "aguardando", "Aguardando"
        TRANSMITINDO = "transmitindo", "Transmitindo"
        ENCERRADA = "encerrada", "Encerrada"

    identificador = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    proprietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salas_proprietario",
    )
    nome = models.CharField(max_length=120)
    codigo_convite = models.CharField(
        max_length=16,
        unique=True,
        default=generate_invite_code,
        editable=False,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AGUARDANDO,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.nome

    @property
    def is_active(self) -> bool:
        return self.status != self.Status.ENCERRADA


class ParticipanteSala(models.Model):
    sala = models.ForeignKey(
        Sala,
        on_delete=models.CASCADE,
        related_name="participantes",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participacoes_sala",
    )
    ativo = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "participante da sala"
        verbose_name_plural = "participantes da sala"
        constraints = [
            models.UniqueConstraint(
                fields=["sala", "usuario"],
                name="unique_participante_por_sala",
            )
        ]
        ordering = ["joined_at"]

    def __str__(self) -> str:
        return f"{self.usuario} em {self.sala}"
