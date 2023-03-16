from django.contrib import admin

from .models import Channel, Log, Message, MessageCategories, User

admin.site.register(User)
admin.site.register(MessageCategories)
admin.site.register(Message)
admin.site.register(Channel)
admin.site.register(Log)
