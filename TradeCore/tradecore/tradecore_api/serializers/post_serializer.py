from rest_framework import serializers
from tradecore_api.models import Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        exclude = ("like",)
