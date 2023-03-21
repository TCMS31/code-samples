import factory

from tradecore_api.models import Post
from tradecore_api.tests.factories.user_factory import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    """Build Post rows, creating an owning user unless one is supplied."""

    class Meta:
        model = Post

    title = factory.Sequence(lambda n: f"Post title {n}")
    description = factory.Sequence(lambda n: f"Post description {n}")
    user = factory.SubFactory(UserFactory)
