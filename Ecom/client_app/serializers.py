from rest_framework import serializers
from .models import *
class UserSerializer(serializers.ModelSerializer):
    class Meta :
        model = User
        fields = '__all__'

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta :
        model = user_details
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    class Meta :
        model = Order
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta :
        model = OrderItem
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta :
        model = product
        fields = '__all__'