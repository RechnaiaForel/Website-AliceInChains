import io

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets, permissions

from .models import Cart, CartItem, Category, Manufacturer, Order, OrderItem, Product
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    CategorySerializer,
    ManufacturerSerializer,
    ProductSerializer,
)


# ---------------------------------------------------------------------------
# Информационные страницы
# ---------------------------------------------------------------------------

def index(request):
    return render(request, 'index.html')


def author(request):
    return HttpResponse("Автор: Дмитрий. Лабораторная работа по Django.")


def about(request):
    return HttpResponse(
        "Интернет-магазин музыкальных инструментов на Django: "
        "каталог товаров с фильтрами и поиском, корзина покупателя "
        "и оформление заказа с отправкой чека на e-mail."
    )


# ---------------------------------------------------------------------------
# Каталог товаров
# ---------------------------------------------------------------------------

def product_list(request):
    products = Product.objects.select_related('category', 'manufacturer').all()

    category_id = request.GET.get('category', '')
    manufacturer_id = request.GET.get('manufacturer', '')
    query = request.GET.get('q', '').strip()

    if category_id:
        products = products.filter(category_id=category_id)

    if manufacturer_id:
        products = products.filter(manufacturer_id=manufacturer_id)

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    context = {
        'products': products,
        'categories': Category.objects.all(),
        'manufacturers': Manufacturer.objects.all(),
        'selected_category': category_id,
        'selected_manufacturer': manufacturer_id,
        'query': query,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_detail.html', {'product': product})


# ---------------------------------------------------------------------------
# Корзина
# ---------------------------------------------------------------------------

@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.cartitem_set.select_related('product').all()
    return render(request, 'shop/cart.html', {
        'cart': cart,
        'items': items,
        'total': cart.total_price(),
    })


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    try:
        quantity_to_add = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity_to_add = 1
    if quantity_to_add < 1:
        quantity_to_add = 1

    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={'quantity': 0}
    )

    new_quantity = item.quantity + quantity_to_add
    if new_quantity > product.quantity_in_stock:
        new_quantity = product.quantity_in_stock

    if new_quantity <= 0:
        item.delete()
        messages.warning(request, "Товара нет в наличии.")
    else:
        item.quantity = new_quantity
        item.save()
        messages.success(request, f"«{product.name}» добавлен в корзину.")

    return redirect('product_detail', pk=product.pk)


@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', item.quantity))
        except (TypeError, ValueError):
            quantity = item.quantity

        if quantity <= 0:
            item.delete()
            messages.info(request, "Товар удалён из корзины.")
        elif quantity > item.product.quantity_in_stock:
            messages.error(
                request,
                f"На складе доступно только {item.product.quantity_in_stock} шт.",
            )
        else:
            item.quantity = quantity
            item.save()
            messages.success(request, "Количество товара обновлено.")

    return redirect('cart_view')


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.info(request, "Товар удалён из корзины.")
    return redirect('cart_view')


# ---------------------------------------------------------------------------
# Оформление заказа
# ---------------------------------------------------------------------------

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = list(cart.cartitem_set.select_related('product').all())

    if not items:
        messages.warning(request, "Ваша корзина пуста.")
        return redirect('cart_view')

    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        if not address:
            messages.error(request, "Укажите адрес доставки.")
            return render(request, 'shop/checkout.html', {
                'items': items,
                'total': cart.total_price(),
            })

        order = Order.objects.create(
            user=request.user,
            delivery_address=address,
            total_price=cart.total_price(),
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            product = item.product
            product.quantity_in_stock = max(0, product.quantity_in_stock - item.quantity)
            product.save()

        send_receipt_email(order)

        cart.cartitem_set.all().delete()

        messages.success(request, f"Заказ №{order.id} успешно оформлен!")
        return redirect('checkout_done', order_id=order.id)

    return render(request, 'shop/checkout.html', {
        'items': items,
        'total': cart.total_price(),
    })


@login_required
def checkout_done(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'shop/checkout_done.html', {'order': order})


def build_receipt(order):
    """Формирует Excel-чек по заказу и возвращает его в виде BytesIO."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Чек'

    sheet.append(['Чек по заказу', f'№{order.id}'])
    sheet.append(['Дата', order.created_at.strftime('%d.%m.%Y %H:%M')])
    sheet.append(['Покупатель', order.user.username])
    sheet.append(['Адрес доставки', order.delivery_address])
    sheet.append([])
    sheet.append(['Товар', 'Количество', 'Цена', 'Сумма'])

    for order_item in order.items.select_related('product').all():
        sheet.append([
            order_item.product.name,
            order_item.quantity,
            float(order_item.price),
            float(order_item.item_price()),
        ])

    sheet.append([])
    sheet.append(['Итого:', '', '', float(order.total_price)])

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def send_receipt_email(order):
    """Отправляет покупателю письмо с чеком в формате Excel."""
    if not order.user.email:
        return

    receipt = build_receipt(order)

    email = EmailMessage(
        subject=f'Чек по заказу №{order.id}',
        body=(
            f'Спасибо за покупку!\n\n'
            f'Заказ №{order.id} оформлен.\n'
            f'Адрес доставки: {order.delivery_address}\n'
            f'Сумма заказа: {order.total_price} руб.\n\n'
            f'Чек прикреплён к письму.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email],
    )
    email.attach(
        f'receipt_{order.id}.xlsx',
        receipt.getvalue(),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    email.send(fail_silently=True)


# ---------------------------------------------------------------------------
# REST API (Django REST Framework)
# ---------------------------------------------------------------------------

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'manufacturer').all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]


class CartViewSet(viewsets.ModelViewSet):
    """
    Каждый пользователь видит и может изменять только свою собственную
    корзину — отдельной для каждого пользователя (OneToOneField), поэтому
    queryset ограничивается текущим пользователем.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    """
    Аналогично CartViewSet: пользователь работает только с элементами
    собственной корзины.
    """
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

