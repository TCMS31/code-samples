from django.db import models
from tradecore_api.models import User


class Post(models.Model):
    user = models.ForeignKey(User, models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    like = models.ManyToManyField(User, related_name="user_likes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
