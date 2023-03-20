from rest_framework.views import APIView
from tradecore_api.models import Post
from tradecore_api.serializers import PostSerializer
from tradecore_api.utils import AccountUtility
from rest_framework.response import Response
from rest_framework import status


class PostUpdateDestroyAPIView(APIView):
    """
    This class handles post endpoints for specific post
    """

    def delete(self, request, **kwargs):
        """
        Handles DELETE method, authenticates user and deletes post
        """
        id = kwargs["id"]
        user = AccountUtility.get_user_data(request.headers.get("Authorization", None))
        if user and AccountUtility.check_post_authorization(user, id):
            try:
                Post.objects.get(id=id).delete()
                return Response(
                    {"message": "Post successfully deleted"}, status=status.HTTP_200_OK
                )
            except Post.DoesNotExist:
                return Response(
                    {"message": "Unable to delete post"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"message": "User is not authenticated/authorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

    def patch(self, request, **kwargs):
        """
        Handles PATCH request, authenticates user and updates post
        """
        id = kwargs["id"]
        data = request.data
        user = AccountUtility.get_user_data(request.headers.get("Authorization", None))
        if user and AccountUtility.check_post_authorization(user, id):
            try:
                post = Post.objects.get(id=id)
                serializer = PostSerializer(post, request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {"post_data": serializer.data}, status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {"validation_error": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Post.DoesNotExist:
                return Response(
                    {"message": "Unable to update post"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"message": "User is not authenticated/authorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
