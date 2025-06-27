from django.contrib import admin
from django.urls import path, include
from client_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),

    #admin
    path('ecomadmin/', include([
        path('login/', views.admin_login, name='admin_login'),
        path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
        path('products/', views.product_management, name='admin_product_management'),
        path('products/add/', views.add_product, name='admin_add_product'),
        path('products/edit/<int:product_id>/', views.edit_product, name='admin_edit_product'),
        path('products/delete/<int:product_id>/', views.delete_product, name='admin_delete_product'),
        path('orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
        path('orders/<int:order_id>/update/', views.admin_order_update, name='admin_order_update'),
        path('orders/', views.admin_order_list, name='admin_order_list'),
    ])),
    
    #client
    path('products/', views.products, name='products'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_user, name='login'),
    path('signup/', views.register_user, name='signup'),
    path('logout/', views.logout_user, name='logout'),
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<str:product_name>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<str:product_name>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('profile/', views.profile, name='profile'),
    path('product/<int:product_id>/', views.product_description, name='product_description'),
    path('order/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/detail/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('my-orders/', views.user_orders_view, name='user_orders'),

    #rest api urls
    path('get-user/', views.get_user, name='get_user'),
    path('post-user/', views.post_user, name='post_user'),
    path('put-user/<int:user_id>/', views.put_user, name='put_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)