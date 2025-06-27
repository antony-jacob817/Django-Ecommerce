from django.contrib import admin
from .models import *

admin.site.register(product)
admin.site.register(user_details)
admin.site.register(Order)
admin.site.register(OrderItem)