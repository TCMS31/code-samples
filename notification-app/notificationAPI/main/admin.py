from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(MessageCategories)
admin.site.register(Message)
admin.site.register(Channel)
admin.site.register(Log)
