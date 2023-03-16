from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from tradecore_api.models import User
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status
from tradecore_api.serializers import UserSerializer


class UserAPIView(APIView):
    """
    This class handles User data
    """

    def get(self, request, **kwargs):
        """
        Handles GET request, returns user data
        """
        try:
            user = get_object_or_404(User, id=kwargs.get("id"))
        except Http404:
            return Response(
                {"message": "User Not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserSerializer(user)
        return Response(
            {
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
