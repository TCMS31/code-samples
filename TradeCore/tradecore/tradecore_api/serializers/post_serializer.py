from rest_framework import serializers
from tradecore_api.models import Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        exclude = ("like",)
        # The owner is always the authenticated caller. Left writable, a PATCH
        # with {"user": <id>} handed the post to another account.
        read_only_fields = ("user",)
