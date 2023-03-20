from rest_framework import serializers
from tradecore_api.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    This class serializes User model.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "geolocation_data",
            "joined_on_holiday",
        )
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
