from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tradecore_api.models import Post
from tradecore_api.serializers import PostSerializer
from tradecore_api.utils import AccountUtility

# Posts are returned newest-first and capped so a large account cannot return an
# unbounded result set in a single response.
MAX_POSTS_PER_RESPONSE = 100


class PostAPIView(APIView):
    """Create posts, list the caller's posts, and like/unlike a post."""

    def _authenticate(self, request):
        return AccountUtility.get_user_data(request.headers.get("Authorization"))

    def post(self, request):
        """Create a post owned by the authenticated user."""
        user = self._authenticate(request)
        if not user:
            return Response(
                {"message": "User is not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = PostSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"validation_error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save(user=user)
        return Response({"post_data": serializer.data}, status=status.HTTP_201_CREATED)

    def get(self, request):
        """Return the authenticated user's posts, newest first."""
        user = self._authenticate(request)
        if not user:
            return Response(
                {"message": "User is not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # select_related on the owner keeps this a single query; the slice bounds it.
        posts = (
            Post.objects.filter(user=user)
            .select_related("user")
            .order_by("-created_at")[:MAX_POSTS_PER_RESPONSE]
        )
        serializer = PostSerializer(posts, many=True)
        return Response({"posts": serializer.data}, status=status.HTTP_200_OK)

    def patch(self, request):
        """Like or unlike a post on behalf of the authenticated user."""
        user = self._authenticate(request)
        if not user:
            return Response(
                {"message": "User is not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        post_id = request.data.get("post_id")
        action = request.data.get("action")
        if not AccountUtility.validate_post_params(post_id, action):
            return Response(
                {
                    "message": "Please provide post_id (str) and action (str)"
                    " (like, unlike) in params"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            post = Post.objects.get(id=post_id)
        except (Post.DoesNotExist, ValueError):
            return Response(
                {"message": "Unable to like/unlike post"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # add()/remove() on a M2M are idempotent, so no read-modify-write is needed.
        if action == "like":
            post.like.add(user)
        else:
            post.like.remove(user)

        return Response(
            {"message": "Action performed successfully"}, status=status.HTTP_200_OK
        )
