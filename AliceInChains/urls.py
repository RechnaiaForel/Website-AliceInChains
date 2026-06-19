from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'manufacturers', views.ManufacturerViewSet, basename='manufacturer')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'carts', views.CartViewSet, basename='cart')
router.register(r'cart-items', views.CartItemViewSet, basename='cartitem')
router.register(r'orders', views.OrderViewSet, basename='order')


urlpatterns = [
    # Информационные страницы
    path('', views.index, name='index'),
    path('author/', views.author, name='author'),
    path('about/', views.about, name='about'),

    # Регистрация и личный кабинет
    path('register/', views.register, name='register'),
    path('profile/', views.profile_view, name='profile_view'),

    # Каталог товаров
    path('catalog/', views.product_list, name='product_list'),
    path('catalog/<int:pk>/', views.product_detail, name='product_detail'),

    # Корзина
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Оформление заказа
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/done/<int:order_id>/', views.checkout_done, name='checkout_done'),

    # REST API (DRF)
    path('api/me/', views.MeAPIView.as_view(), name='api_me'),
    path('api/cart/add/', views.cart_add_api, name='api_cart_add'),
    path('api/', include(router.urls)),
]
