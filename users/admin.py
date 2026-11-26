from django.contrib import admin

from .models import Address, User

# Register your models here.
admin.site.register((User, Address))