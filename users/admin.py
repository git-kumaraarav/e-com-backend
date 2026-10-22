from django.contrib import admin
from .models import User, Address, UserProfile

# Register your models here.
admin.site.register((User, Address, UserProfile))