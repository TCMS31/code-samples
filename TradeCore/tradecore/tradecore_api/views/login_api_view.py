from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from tradecore_api.utils import AccountUtility
from django.contrib.auth import authenticate
from django.utils import timezone
from tradecore_api.serializers import UserSerializer


class LoginAPIView(APIView):
    """
    This class handles login endpoint
    """

    def post(self, request):
        """
        Handle POST request, return authentication token and success/failure messages along with HTTP status code.
        """
        email = request.data.get("email", None)
        password = request.data.get("password", None)

        if not AccountUtility.validate_account_params(email, password):
            return Response(
                {"message": "Please provide email(str) and password(str)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # User.save() lowercases the stored address, so the lookup must match.
        # Without this, signing up as "Ada@Example.com" and logging in with the
        # same string fails.
        user = authenticate(email=email.lower(), password=password)
        if user:
            token = AccountUtility.get_token(user)
            serialized_user = UserSerializer(user)
            response = {"user": serialized_user.data, "token": token}
            status_code = status.HTTP_200_OK
            user.token_authenticated_at = timezone.now()
            user.save()
        else:
            response = {"message": "Invalid email or password"}
            status_code = status.HTTP_401_UNAUTHORIZED

        return Response(response, status=status_code)
