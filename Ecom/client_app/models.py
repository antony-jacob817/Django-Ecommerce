from django.db import models
from django.contrib.auth.models import User  # or your custom User model
from django.dispatch import receiver
from django.db.models.signals import post_save

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  # If you have user accounts
    session_key = models.CharField(max_length=100, blank=True)  # For guest checkouts
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending', 
                            choices=[
                                ('pending', 'Pending'),
                                ('completed', 'Completed'),
                                ('cancelled', 'Cancelled')
                            ])

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

class product(models.Model):
    name = models.CharField(max_length=100, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    stock = models.IntegerField(null=True)
    brand = models.CharField(max_length=50, null=True)
    description = models.TextField(null=True)
    featured = models.BooleanField(default=False)
    free_shipping = models.BooleanField(default=False)
    product_image = models.ImageField(upload_to='media', null=True)
    category = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.name

class user_details(models.Model):
    name = models.CharField(max_length=50, null=True)
    email = models.EmailField(max_length=50, null=True)
    phone = models.CharField(max_length=10, null=True)
    password = models.CharField(max_length=50, null=True)
    terms = models.BooleanField(default=False)
