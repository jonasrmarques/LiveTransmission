"""Custom user model for LiveTransmission."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extends Django's AbstractUser.

    Email is required and unique to support future password recovery
    and profile features without a parallel auth system.
    """

    email = models.EmailField("e-mail", unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username
