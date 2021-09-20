from django.contrib import admin

from .models import Payment, Travel, Friendship

admin.site.register(Payment)
admin.site.register(Friendship)
admin.site.register(Travel)
