from django.urls import path

from .views import (
    CreateMessageAPIView,
    LogListView,
    LogStringListView,
    MessageCategoryListView,
)

urlpatterns = [
    path("logs/", LogListView.as_view(), name="log-list"),
    path("logs/string", LogStringListView.as_view(), name="log-list-string"),
    path("add/", CreateMessageAPIView.as_view(), name="add-message"),
    path("categories/", MessageCategoryListView.as_view(), name="category-list"),
]
