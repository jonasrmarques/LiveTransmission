"""Business logic for the usuarios domain."""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction

User = get_user_model()


class UserServiceError(Exception):
    """Base error for user domain operations."""


class UserAlreadyExistsError(UserServiceError):
    """Raised when username or email is already registered."""


class InvalidCredentialsError(UserServiceError):
    """Raised when login credentials are invalid."""


@transaction.atomic
def register_user(*, username: str, email: str, password: str) -> User:
    """Create a new active user. Does not log the user in."""
    username = username.strip()
    email = email.strip().lower()

    if User.objects.filter(username__iexact=username).exists():
        raise UserAlreadyExistsError("Nome de usuário já está em uso.")
    if User.objects.filter(email__iexact=email).exists():
        raise UserAlreadyExistsError("E-mail já está em uso.")

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
    except IntegrityError as exc:
        raise UserAlreadyExistsError("Não foi possível criar o usuário.") from exc

    return user


def login_user(request, *, username: str, password: str) -> User:
    """Authenticate credentials and establish a session."""
    user = authenticate(
        request,
        username=username.strip(),
        password=password,
    )
    if user is None:
        raise InvalidCredentialsError("Usuário ou senha inválidos.")

    login(request, user)
    return user


def logout_user(request) -> None:
    """End the current session."""
    logout(request)


def update_profile(user: User, *, email: str | None = None, first_name: str | None = None, last_name: str | None = None) -> User:
    """Update mutable profile fields for the given user."""
    if email is not None:
        email = email.strip().lower()
        if (
            User.objects.filter(email__iexact=email)
            .exclude(pk=user.pk)
            .exists()
        ):
            raise UserAlreadyExistsError("E-mail já está em uso.")
        user.email = email

    if first_name is not None:
        user.first_name = first_name.strip()
    if last_name is not None:
        user.last_name = last_name.strip()

    try:
        user.save()
    except IntegrityError as exc:
        raise UserAlreadyExistsError("Não foi possível atualizar o perfil.") from exc

    return user
