"""Tests for room creation, access, join/leave and permissions."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from transmissao.models import Sala
from transmissao.services import (
    SalaAccessDeniedError,
    create_sala,
    end_transmission,
    join_sala,
    join_sala_by_code,
    leave_sala,
    remove_participant,
    start_transmission,
)
from usuarios.services import register_user

User = get_user_model()


class SalaServiceTests(TestCase):
    def setUp(self):
        self.owner = register_user(
            username="owner",
            email="owner@example.com",
            password="Str0ng-Pass!",
        )
        self.guest = register_user(
            username="guest",
            email="guest@example.com",
            password="Str0ng-Pass!",
        )

    def test_create_sala_adds_owner_as_participant(self):
        sala = create_sala(owner=self.owner, nome="Minha Sala")
        self.assertEqual(sala.proprietario, self.owner)
        self.assertTrue(sala.participantes.filter(usuario=self.owner, ativo=True).exists())

    def test_join_and_leave_sala(self):
        sala = create_sala(owner=self.owner, nome="Sala")
        join_sala(sala=sala, user=self.guest)
        self.assertTrue(sala.participantes.filter(usuario=self.guest, ativo=True).exists())
        leave_sala(sala=sala, user=self.guest)
        self.assertFalse(sala.participantes.filter(usuario=self.guest, ativo=True).exists())

    def test_join_by_code(self):
        sala = create_sala(owner=self.owner, nome="Sala")
        joined = join_sala_by_code(codigo=sala.codigo_convite, user=self.guest)
        self.assertEqual(joined.id, sala.id)

    def test_start_and_end_transmission(self):
        sala = create_sala(owner=self.owner, nome="Sala")
        start_transmission(sala=sala, owner=self.owner)
        sala.refresh_from_db()
        self.assertEqual(sala.status, Sala.Status.TRANSMITINDO)
        end_transmission(sala=sala, owner=self.owner)
        sala.refresh_from_db()
        self.assertEqual(sala.status, Sala.Status.ENCERRADA)

    def test_remove_participant_by_owner(self):
        sala = create_sala(owner=self.owner, nome="Sala")
        join_sala(sala=sala, user=self.guest)
        remove_participant(sala=sala, owner=self.owner, participant=self.guest)
        self.assertFalse(sala.participantes.filter(usuario=self.guest, ativo=True).exists())

    def test_non_owner_cannot_remove_participant(self):
        sala = create_sala(owner=self.owner, nome="Sala")
        join_sala(sala=sala, user=self.guest)
        other = register_user(
            username="other",
            email="other@example.com",
            password="Str0ng-Pass!",
        )
        join_sala(sala=sala, user=other)
        with self.assertRaises(SalaAccessDeniedError):
            remove_participant(sala=sala, owner=self.guest, participant=other)


class SalaAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "Str0ng-Pass!"
        self.owner = register_user(
            username="owner",
            email="owner@example.com",
            password=self.password,
        )
        self.guest = register_user(
            username="guest",
            email="guest@example.com",
            password=self.password,
        )
        self.sala = create_sala(owner=self.owner, nome="Sala API")

    def test_create_sala_api(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api-transmissao-salas"),
            {"nome": "Nova Sala"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nome"], "Nova Sala")
        self.assertTrue(response.data["is_owner"])

    def test_list_salas_api(self):
        join_sala(sala=self.sala, user=self.guest)
        self.client.force_authenticate(user=self.guest)
        response = self.client.get(reverse("api-transmissao-salas"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_entrar_por_codigo_api(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            reverse("api-transmissao-salas-entrar-codigo"),
            {"codigo": self.sala.codigo_convite},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["identificador"], str(self.sala.identificador))

    def test_detail_requires_participant(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get(
            reverse(
                "api-transmissao-sala-detail",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_allowed_for_participant(self):
        join_sala(sala=self.sala, user=self.guest)
        self.client.force_authenticate(user=self.guest)
        response = self.client.get(
            reverse(
                "api-transmissao-sala-detail",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_start_transmission(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse(
                "api-transmissao-sala-iniciar",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Sala.Status.TRANSMITINDO)

    def test_guest_cannot_start_transmission(self):
        join_sala(sala=self.sala, user=self.guest)
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            reverse(
                "api-transmissao-sala-iniciar",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sair_api(self):
        join_sala(sala=self.sala, user=self.guest)
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            reverse(
                "api-transmissao-sala-sair",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sair_apos_encerrar_e_idempotente(self):
        join_sala(sala=self.sala, user=self.guest)
        end_transmission(sala=self.sala, owner=self.owner)
        self.client.force_authenticate(user=self.guest)
        response = self.client.post(
            reverse(
                "api-transmissao-sala-sair",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Second leave also succeeds.
        response2 = self.client.post(
            reverse(
                "api-transmissao-sala-sair",
                kwargs={"identificador": self.sala.identificador},
            )
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_owner_remove_participant_api(self):
        join_sala(sala=self.sala, user=self.guest)
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            reverse(
                "api-transmissao-sala-remover-participante",
                kwargs={
                    "identificador": self.sala.identificador,
                    "user_id": self.guest.id,
                },
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
