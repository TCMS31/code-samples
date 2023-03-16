from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from tradecore_api.models import Post
from tradecore_api.tests.factories import PostFactory, UserFactory
from tradecore_api.utils import AccountUtility


class PostAPITestCase(APITestCase):
    """Shared helpers for the authenticated post endpoints."""

    def setUp(self):
        self.user = UserFactory.create()
        self.other_user = UserFactory.create()
        self.auth = {"HTTP_AUTHORIZATION": f"JWT {AccountUtility.get_token(self.user)}"}


class PostCreationTests(PostAPITestCase):
    def test_factory_persists_a_post_with_an_owner(self):
        post = PostFactory.create()
        self.assertEqual(Post.objects.get(id=post.id).title, post.title)
        self.assertIsNotNone(post.user)

    def test_create_post_assigns_the_authenticated_user_as_owner(self):
        response = self.client.post(
            reverse("post-get-create"),
            data={"title": "Hello", "description": "World"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(title="Hello")
        self.assertEqual(post.user_id, self.user.id)

    def test_create_post_requires_authentication(self):
        response = self.client.post(
            reverse("post-get-create"),
            data={"title": "Hello", "description": "World"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Post.objects.filter(title="Hello").exists())

    def test_create_post_rejects_a_garbage_token(self):
        response = self.client.post(
            reverse("post-get-create"),
            data={"title": "Hello", "description": "World"},
            format="json",
            HTTP_AUTHORIZATION="JWT not-a-real-token",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_post_validates_the_payload(self):
        response = self.client.post(
            reverse("post-get-create"), data={}, format="json", **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data["validation_error"])


class PostListTests(PostAPITestCase):
    def test_list_returns_only_the_callers_posts(self):
        PostFactory.create_batch(3, user=self.user)
        PostFactory.create_batch(2, user=self.other_user)

        response = self.client.get(reverse("post-get-create"), **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["posts"]), 3)

    def test_list_query_count_does_not_grow_with_row_count(self):
        """select_related keeps listing off an N+1 path.

        Two queries are expected in both cases: one to resolve the bearer token
        to a user, one to fetch the posts. The point of the test is that the
        second number is identical to the first.
        """
        PostFactory.create_batch(3, user=self.user)
        with self.assertNumQueries(2):
            self.client.get(reverse("post-get-create"), **self.auth).render()

        PostFactory.create_batch(27, user=self.user)
        with self.assertNumQueries(2):
            response = self.client.get(reverse("post-get-create"), **self.auth)
            response.render()
        self.assertEqual(len(response.data["posts"]), 30)


class PostLikeTests(PostAPITestCase):
    def test_like_then_unlike_a_post(self):
        post = PostFactory.create(user=self.other_user)

        like = self.client.patch(
            reverse("post-get-create"),
            data={"post_id": str(post.id), "action": "like"},
            format="json",
            **self.auth,
        )
        self.assertEqual(like.status_code, status.HTTP_200_OK)
        self.assertIn(self.user, post.like.all())

        unlike = self.client.patch(
            reverse("post-get-create"),
            data={"post_id": str(post.id), "action": "unlike"},
            format="json",
            **self.auth,
        )
        self.assertEqual(unlike.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.user, post.like.all())

    def test_liking_twice_does_not_duplicate_the_like(self):
        post = PostFactory.create(user=self.other_user)
        payload = {"post_id": str(post.id), "action": "like"}
        self.client.patch(
            reverse("post-get-create"), data=payload, format="json", **self.auth
        )
        self.client.patch(
            reverse("post-get-create"), data=payload, format="json", **self.auth
        )
        self.assertEqual(post.like.count(), 1)

    def test_rejects_an_unknown_action(self):
        post = PostFactory.create(user=self.other_user)
        response = self.client.patch(
            reverse("post-get-create"),
            data={"post_id": str(post.id), "action": "destroy"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_returns_404_for_an_unknown_post(self):
        response = self.client.patch(
            reverse("post-get-create"),
            data={"post_id": "999999", "action": "like"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PostUpdateDeleteTests(PostAPITestCase):
    def test_owner_can_update_their_post(self):
        post = PostFactory.create(user=self.user)
        response = self.client.patch(
            reverse("post-update-delete", kwargs={"id": post.id}),
            data={"title": "Updated title"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.title, "Updated title")

    def test_non_owner_cannot_update_a_post(self):
        post = PostFactory.create(user=self.other_user)
        response = self.client.patch(
            reverse("post-update-delete", kwargs={"id": post.id}),
            data={"title": "Hijacked"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        post.refresh_from_db()
        self.assertNotEqual(post.title, "Hijacked")

    def test_update_reports_validation_errors(self):
        """Regression: this branch referenced ``serializer.erros`` and crashed."""
        post = PostFactory.create(user=self.user)
        response = self.client.patch(
            reverse("post-update-delete", kwargs={"id": post.id}),
            data={"title": "x" * 300},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data["validation_error"])

    def test_owner_can_delete_their_post(self):
        post = PostFactory.create(user=self.user)
        response = self.client.delete(
            reverse("post-update-delete", kwargs={"id": post.id}), **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_non_owner_cannot_delete_a_post(self):
        post = PostFactory.create(user=self.other_user)
        response = self.client.delete(
            reverse("post-update-delete", kwargs={"id": post.id}), **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Post.objects.filter(id=post.id).exists())
