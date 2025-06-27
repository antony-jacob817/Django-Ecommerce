from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .serializers import *
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

def is_admin(user):
    """Check if user is admin (superuser or staff)"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

def admin_login(request):
    # If user is already authenticated but not superuser
    if request.user.is_authenticated and not request.user.is_superuser:
        return render(request, 'ecomadmin/access_denied.html')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient privileges')
    
    return render(request, 'ecomadmin/login.html')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    stats = {
        'total_products': product.objects.count(),
        'featured_products': product.objects.filter(featured=True).count(),
        'low_stock': product.objects.filter(stock__lt=10).count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'recent_orders': Order.objects.order_by('-created_at')[:10],
        'products': product.objects.all().order_by('-id')[:10]
    }
    return render(request, 'ecomadmin/dashboard.html', stats)

@login_required
@user_passes_test(is_admin)
def product_management(request):
    """Product management with search and filters"""
    products = product.objects.all().order_by('-id')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query))
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category=category_filter)
    
    # Filter by stock status
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'low':
        products = products.filter(stock__lt=10)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get distinct categories for filter dropdown
    categories = product.objects.values_list('category', flat=True).distinct()
    
    context = {
        'products': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_filter,
        'selected_stock': stock_filter,
    }
    return render(request, 'ecomadmin/product_management.html', context)

@login_required
@user_passes_test(is_admin)
def add_product(request):
    """Add new product with validation"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Validate required fields
                required_fields = ['name', 'price', 'stock']
                errors = {}
                for field in required_fields:
                    if not request.POST.get(field):
                        errors[field] = 'This field is required'
                
                # Special handling for category
                category_option = request.POST.get('category')
                if not category_option:
                    errors['category'] = 'This field is required'
                elif category_option == 'new_category' and not request.POST.get('new_category_name'):
                    errors['category'] = 'Please enter a new category name'
                
                if errors:
                    for field, error in errors.items():
                        messages.error(request, f'{field}: {error}')
                    return redirect(reverse('admin_add_product'))
                
                # Validate price and stock
                try:
                    price = float(request.POST.get('price'))
                    stock = int(request.POST.get('stock'))
                except ValueError:
                    messages.error(request, 'Price must be a number and stock must be an integer')
                    return redirect(reverse('admin_add_product'))
                
                # Handle category
                if category_option == 'new_category':
                    # Get or create the new category (capitalize first letter)
                    new_category_name = request.POST.get('new_category_name').strip()
                    if new_category_name:
                        # Capitalize first letter and lowercase the rest
                        new_category_name = new_category_name[0].upper() + new_category_name[1:].lower()
                        # Check if category already exists
                        if product.objects.filter(category__iexact=new_category_name).exists():
                            category = new_category_name
                        else:
                            category = new_category_name
                    else:
                        messages.error(request, 'Please enter a valid category name')
                        return redirect(reverse('admin_add_product'))
                else:
                    category = category_option
                
                # Create product
                new_product = product(
                    name=request.POST.get('name'),
                    price=price,
                    stock=stock,
                    brand=request.POST.get('brand', ''),
                    description=request.POST.get('description', ''),
                    featured=request.POST.get('featured') == 'on',
                    free_shipping=request.POST.get('free_shipping') == 'on',
                    category=category,
                )
                
                # Handle image upload
                if 'product_image' in request.FILES:
                    image = request.FILES['product_image']
                    if image.size > 5*1024*1024:  # 5MB limit
                        messages.error(request, 'Image too large (max 5MB)')
                        return redirect(reverse('admin_add_product'))
                    new_product.product_image = image
                
                new_product.save()
                messages.success(request, 'Product added successfully!')
                return redirect(reverse('admin_product_management'))
        
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
            return redirect(reverse('admin_add_product'))
    
    # GET request - show form
    # Get all distinct categories from existing products
    categories = product.objects.exclude(category__isnull=True).exclude(category__exact='').values_list('category', flat=True).distinct()
    return render(request, 'ecomadmin/addproduct.html', {'categories': categories})

@login_required
@user_passes_test(is_admin)
def edit_product(request, product_id):
    """Edit existing product with validation"""
    product_obj = get_object_or_404(product, id=product_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Validate required fields
                required_fields = ['name', 'price', 'stock']
                errors = {}
                for field in required_fields:
                    if not request.POST.get(field):
                        errors[field] = 'This field is required'
                
                # Special handling for category
                category_option = request.POST.get('category')
                if not category_option:
                    errors['category'] = 'This field is required'
                elif category_option == 'new_category' and not request.POST.get('new_category_name'):
                    errors['category'] = 'Please enter a new category name'
                
                if errors:
                    for field, error in errors.items():
                        messages.error(request, f'{field}: {error}')
                    return redirect(reverse('admin_edit_product', args=[product_id]))
                
                # Validate price and stock
                try:
                    price = float(request.POST.get('price'))
                    stock = int(request.POST.get('stock'))
                except ValueError:
                    messages.error(request, 'Price must be a number and stock must be an integer')
                    return redirect(reverse('admin_edit_product', args=[product_id]))
                
                # Handle category
                if category_option == 'new_category':
                    # Get or create the new category (capitalize first letter)
                    new_category_name = request.POST.get('new_category_name').strip()
                    if new_category_name:
                        # Capitalize first letter and lowercase the rest
                        new_category_name = new_category_name[0].upper() + new_category_name[1:].lower()
                        category = new_category_name
                    else:
                        messages.error(request, 'Please enter a valid category name')
                        return redirect(reverse('admin_edit_product', args=[product_id]))
                else:
                    category = category_option
                
                # Update product
                product_obj.name = request.POST.get('name')
                product_obj.price = price
                product_obj.stock = stock
                product_obj.brand = request.POST.get('brand', '')
                product_obj.description = request.POST.get('description', '')
                product_obj.featured = request.POST.get('featured') == 'on'
                product_obj.free_shipping = request.POST.get('free_shipping') == 'on'
                product_obj.category = category
                
                # Handle image upload/removal
                if 'clear_image' in request.POST:
                    if product_obj.product_image:
                        product_obj.product_image.delete(save=False)
                    product_obj.product_image = None
                elif 'product_image' in request.FILES:
                    image = request.FILES['product_image']
                    if image.size > 5*1024*1024:  # 5MB limit
                        messages.error(request, 'Image too large (max 5MB)')
                        return redirect(reverse('admin_edit_product', args=[product_id]))
                    if product_obj.product_image:
                        product_obj.product_image.delete(save=False)
                    product_obj.product_image = image
                
                product_obj.save()
                messages.success(request, 'Product updated successfully!')
                return redirect(reverse('admin_product_management'))
        
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
            return redirect(reverse('admin_edit_product', args=[product_id]))
    
    # GET request - show form
    # Get all distinct categories from existing products
    categories = product.objects.exclude(category__isnull=True).exclude(category__exact='').values_list('category', flat=True).distinct()
    return render(request, 'ecomadmin/editproduct.html', {
        'product': product_obj,
        'categories': categories,
    })

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_product(request, product_id):
    """Delete product with confirmation and proper image handling"""
    product_obj = get_object_or_404(product, id=product_id)
    try:
        # Delete the associated image file if it exists
        if product_obj.product_image:
            product_obj.product_image.delete(save=False)
        product_obj.delete()
        messages.success(request, 'Product deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting product: {str(e)}')
    return redirect(reverse('admin_product_management'))

@login_required
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'completed', 'cancelled']:
            order.status = new_status
            order.save()
            messages.success(request, f'Order status updated to {new_status}')
            return redirect('admin_order_detail', order_id=order.id)
    
    return render(request, 'ecomadmin/order_detail.html', {
        'order': order,
        'title': f'Order #{order.id}'
    })

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_order_update(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if new_status not in ['pending', 'completed', 'cancelled']:
        messages.error(request, 'Invalid status')
        return redirect('admin_order_detail', order_id=order.id)
    
    order.status = new_status
    order.save()
    
    messages.success(request, f'Order status updated to {new_status}')
    return redirect('admin_order_detail', order_id=order.id)

def check_email(request):
    email = request.GET.get('email', '')
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'exists': exists})

@login_required
def profile(request):
    if request.method == 'POST':
        new_username = request.POST.get('username')
        new_email = request.POST.get('email')
        new_first_name = request.POST.get('first_name')
        new_last_name = request.POST.get('last_name')
        
        if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
            messages.error(request, 'This email address is already in use by another account.')
            return redirect('profile')
        
        if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
            messages.error(request, 'This username is already taken.')
            return redirect('profile')
        
        request.user.username = new_username
        request.user.email = new_email
        request.user.first_name = new_first_name
        request.user.last_name = new_last_name
        request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'profile.html', {
        'title': 'My Profile'
    })

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_confirmation.html', {
        'order': order,
        'title': f'Order Confirmation #{order.id}'
    })

def home(request):
    featured_products = product.objects.filter(featured=True)[:4]
    return render(request, 'home.html', {
        'featured_products': featured_products,
        'title': 'ShopEase - Home'
    })

def products(request):
    search_query = request.GET.get('q')
    category = request.GET.get('category')
    products_list = product.objects.all()
    if category:
        products_list = products_list.filter(category=category)
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    categories = product.objects.values_list('category', flat=True).distinct()

    return render(request, 'products.html', {
        'products': products_list,
        'categories': categories,
        'selected_category': category,
        'search_query': search_query,
        'title': 'ShopEase - Products'
    })

def contact(request):
    return render(request, 'contact.html', {
        'title': 'ShopEase - Contact'
    })

def register_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        if not (username and email and password):
            messages.error(request, "Please fill all fields")
            return redirect('signup')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('signup')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Registration successful! Please login.")
        return redirect('login')
    
    return render(request, 'signup.html')

def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid credentials")
    
    return render(request, 'login.html', {
        'next': request.GET.get('next', '')
    })

def logout_user(request):
    logout(request)
    return redirect('home')

@login_required
@user_passes_test(is_admin)
def admin_order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        ).distinct()
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'search_query': search_query,
        'selected_status': status_filter,
    }
    return render(request, 'ecomadmin/order_list.html', context)

@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    products_in_cart = []
    total = 0
    
    for product_name, item in cart.items():
        try:
            product_obj = product.objects.get(name=product_name)
            item_total = product_obj.price * item['quantity']
            total += item_total
            
            products_in_cart.append({
                'product': product_obj,
                'quantity': item['quantity'],
                'item_total': item_total
            })
        except product.DoesNotExist:
            # Remove non-existent products from cart
            del cart[product_name]
            request.session['cart'] = cart
            request.session.modified = True
    
    return render(request, 'cart.html', {
        'products': products_in_cart,
        'total': total
    })

@login_required
def add_to_cart(request, product_id):
    product_obj = get_object_or_404(product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    cart = request.session.get('cart', {})
    
    if product_obj.name in cart:
        cart[product_obj.name]['quantity'] += quantity
    else:
        cart[product_obj.name] = {
            'quantity': quantity,
            'price': float(product_obj.price)
        }
    
    request.session['cart'] = cart
    return redirect('product_description', product_id=product_id)

@login_required
def update_cart(request, product_name):
    quantity = int(request.POST.get('quantity', 1))
    
    cart = request.session.get('cart', {})
    if product_name in cart:
        cart[product_name]['quantity'] = quantity
        request.session['cart'] = cart
    
    return redirect('cart_view')

@login_required
def remove_from_cart(request, product_name):
    cart = request.session.get('cart', {})
    if product_name in cart:
        del cart[product_name]
        request.session['cart'] = cart
    
    return redirect('cart_view')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.error(request, "Your cart is empty")
        return redirect('cart_view')
    
    try:
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                user=request.user,
                total_amount=sum(item['price']*item['quantity'] for item in cart.values()),
                status='pending'
            )
            
            # Process each item
            for product_name, item in cart.items():
                product_obj = product.objects.select_for_update().get(name=product_name)
                
                # Validate stock
                if product_obj.stock < item['quantity']:
                    raise ValidationError(f'Not enough stock for {product_name}')
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product_name=product_name,
                    quantity=item['quantity'],
                    price=item['price']
                )
                
                # Reduce stock
                product_obj.stock -= item['quantity']
                product_obj.save()
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            
            return redirect('order_confirmation', order_id=order.id)
            
    except product.DoesNotExist as e:
        messages.error(request, f"Product not found: {str(e)}")
        return redirect('cart_view')
        
    except Exception as e:
        messages.error(request, f"Checkout error: {str(e)}")
        return redirect('cart_view')

def product_description(request, product_id):
    product_item = get_object_or_404(product, id=product_id)
    return render(request, 'description.html', {
        'product': product_item,
        'title': f'{product_item.name} - ShopEase'
    })

@login_required
def user_orders_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Date filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
    elif start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    elif end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    # Status filter
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'user_orders.html', {
        'orders': page_obj,
        'status_choices': ['pending', 'completed', 'cancelled'],
        'title': 'My Orders'
    })

@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {
        'order': order,
        'title': f'Order #{order.id} Details'
    })

#rest api views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user(request):
    user_data = User.objects.all()
    serializer = UserSerializer(user_data, many=True)
    return Response(serializer.data)

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def post_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        if not (username and email and password):
            messages.error(request, "Please fill all fields")
            return redirect('signup')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('signup')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        return Response("Success")
    return Response("Please Fill ")

@api_view(['PUT', 'GET'])
@permission_classes([IsAuthenticated])
def put_user(request, user_id):
    user = User.objects.filter(id=user_id)
    if request.method == "PUT":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        user.update(username=username, email=email, password=password)
        return Response("Success")
    return Response("Error")

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.delete()
    return Response("Success")
