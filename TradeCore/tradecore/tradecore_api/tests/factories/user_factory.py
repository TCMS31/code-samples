import factory

from tradecore_api.models import User

# Plain-text password shared by every factory-built user so tests can log in.
DEFAULT_PASSWORD = "factory-pass-123"


class UserFactory(factory.django.DjangoModelFactory):
    """Build User rows with a correctly hashed password.

    ``_create`` is overridden to go through ``UserManager.create_user``. The
    default DjangoModelFactory path calls ``Model.objects.create``, which writes
    the password column verbatim and leaves an unusable plain-text value that no
    login can ever match.
    """

    class Meta:
        model = User

    # Sequences (not bare faker calls evaluated once at import) so each
    # instance really is distinct.
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    geolocation_data = {}
    password = DEFAULT_PASSWORD

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", DEFAULT_PASSWORD)
        email = kwargs.pop("email")
        return model_class.objects.create_user(email=email, password=password, **kwargs)
