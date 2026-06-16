from django.urls import path
from . import views

urlpatterns = [
    # Информационные страницы
    path('', views.index, name='index'),
    path('author/', views.author, name='author'),
    path('about/', views.about, name='about'),

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
]
