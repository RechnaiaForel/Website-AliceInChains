import io

import openpyxl
from django.contrib import messages
from django.contrib.auth import login as auth_login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import RegistrationForm, ProfileUpdateForm
from .models import Cart, CartItem, Category, Manufacturer, Order, OrderItem, Product, Profile
from .permissions import IsAdminOrReadOnly
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    CategorySerializer,
    ManufacturerSerializer,
    OrderSerializer,
    ProductSerializer,
    ProfileSerializer,
)


# ---------------------------------------------------------------------------
# Информационные страницы
# ---------------------------------------------------------------------------

def index(request):
    popular_products = Product.objects.select_related('category', 'manufacturer').order_by('-id')[:6]
    categories = Category.objects.all()
    return render(request, 'shop/index.html', {
        'popular_products': popular_products,
        'categories': categories,
    })


def author(request):
    return HttpResponse("Автор: Дмитрий. Лабораторная работа по Django.")


def about(request):
    return HttpResponse(
        "Интернет-магазин музыкальных инструментов на Django: "
        "каталог товаров с фильтрами и поиском, корзина покупателя "
        "и оформление заказа с отправкой чека на e-mail."
    )


def register(request):
    if request.user.is_authenticated:
        return redirect('profile_view')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Регистрация прошла успешно! Добро пожаловать.")
            return redirect('profile_view')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def profile_view(request):
    """
    Личный кабинет. Доступен всем — но данные профиля и заказы
    подгружаются через JS (fetch /api/me/ и /api/orders/) только для
    аутентифицированных пользователей; для гостей шаблон сам покажет
    сообщение с предложением войти.
    """
    return render(request, 'shop/profile.html')


@login_required
def settings_view(request):
    """
    Страница «Настройки»: смена email/профиля и смена пароля.
    Две формы на одной странице, различаем их по скрытому полю `form_type`.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)

    profile_form  = ProfileUpdateForm(instance=profile,
                                      initial={'email': request.user.email})
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            profile_form = ProfileUpdateForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                # Обновляем email у самого User
                new_email = profile_form.cleaned_data.get('email', '').strip()
                if new_email:
                    request.user.email = new_email
                    request.user.save(update_fields=['email'])
                messages.success(request, 'Данные профиля обновлены.')
                return redirect('settings_view')

        elif form_type == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Сохраняем сессию после смены пароля (без этого — разлогин)
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменён.')
                return redirect('settings_view')

    return render(request, 'shop/settings.html', {
        'profile_form':  profile_form,
        'password_form': password_form,
    })


# ---------------------------------------------------------------------------
# Каталог товаров
# ---------------------------------------------------------------------------

def product_list(request):
    """
    Каталог товаров. Сама страница рендерится на сервере (фильтры,
    разметка), а сетка товаров и пагинация загружаются через JS из
    /api/products/ (см. static/js/main.js). DRF-пагинация ProductViewSet
    использует под капотом тот же класс Paginator из Django.
    """
    context = {
        'categories': Category.objects.all(),
        'manufacturers': Manufacturer.objects.all(),
        'selected_category': request.GET.get('category', ''),
        'selected_manufacturer': request.GET.get('manufacturer', ''),
        'query': request.GET.get('search', ''),
    }
    return render(request, 'shop/catalog.html', context)


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
    """Каталог категорий: чтение доступно всем, запись — только админам."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ManufacturerViewSet(viewsets.ModelViewSet):
    """Производители: чтение доступно всем, запись — только админам."""
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    """
    Товары: чтение (в т.ч. анонимам) доступно всем — этим эндпоинтом
    пользуется static/js/main.js на странице каталога. Создание,
    изменение и удаление — только администраторам (is_staff=True).
    Поддерживает фильтрацию через query-параметры: ?category=<id>,
    ?manufacturer=<id>, ?search=<текст>.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'manufacturer').order_by('-id')

        category_id = self.request.query_params.get('category')
        manufacturer_id = self.request.query_params.get('manufacturer')
        search = self.request.query_params.get('search') or self.request.query_params.get('q')

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if manufacturer_id:
            queryset = queryset.filter(manufacturer_id=manufacturer_id)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return queryset


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


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Только чтение: обычный пользователь видит лишь свои заказы,
    администратор (is_staff) — все заказы всех пользователей.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Order.objects
            .select_related('user')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)


class MeAPIView(APIView):
    """
    GET  /api/me/ — данные профиля текущего пользователя.
    PATCH /api/me/ — изменение профиля (full_name, phone, address).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cart_add_api(request):
    """
    JSON-эндпоинт для кнопки "В корзину" на страницах каталога/товара,
    вызывается через fetch() из static/js/main.js.
    Тело запроса: {"product_id": <id>, "quantity": <int, по умолчанию 1>}.
    """
    product_id = request.data.get('product_id')
    product = get_object_or_404(Product, pk=product_id)

    try:
        quantity_to_add = int(request.data.get('quantity', 1))
    except (TypeError, ValueError):
        quantity_to_add = 1
    if quantity_to_add < 1:
        quantity_to_add = 1

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, _ = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': 0})

    new_quantity = item.quantity + quantity_to_add
    if new_quantity > product.quantity_in_stock:
        new_quantity = product.quantity_in_stock

    if new_quantity <= 0:
        item.delete()
        return Response({'detail': 'Товара нет в наличии.'}, status=status.HTTP_400_BAD_REQUEST)

    item.quantity = new_quantity
    item.save()
    return Response(
        {
            'detail': f'«{product.name}» добавлен в корзину.',
            'quantity': item.quantity,
        },
        status=status.HTTP_200_OK,
    )

