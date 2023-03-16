from django.urls import path

from tradecore_api.views import (
    LoginAPIView,
    PostAPIView,
    PostUpdateDestroyAPIView,
    SignUpAPIView,
    UserAPIView,
)

urlpatterns = [
    path("login", LoginAPIView.as_view(), name="login"),
    path("signup", SignUpAPIView.as_view(), name="signup"),
    path("user/<int:id>", UserAPIView.as_view(), name="user"),
    path("post", PostAPIView.as_view(), name="post-get-create"),
    path(
        "post/<int:id>", PostUpdateDestroyAPIView.as_view(), name="post-update-delete"
    ),
]
