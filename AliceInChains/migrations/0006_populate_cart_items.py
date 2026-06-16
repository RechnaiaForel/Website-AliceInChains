from django.db import migrations


# (cart_id -> [(product_id, quantity), ...])
SAMPLE_ITEMS = {
    1: [(1, 1), (4, 1)],
    2: [(2, 1), (6, 2)],
    3: [(10, 1), (14, 1)],
    4: [(18, 1), (23, 1)],
    5: [(25, 2), (8, 1)],
}


def add_cart_items(apps, schema_editor):
    Cart = apps.get_model('AliceInChains', 'Cart')
    CartItem = apps.get_model('AliceInChains', 'CartItem')
    Product = apps.get_model('AliceInChains', 'Product')

    for cart_id, items in SAMPLE_ITEMS.items():
        try:
            cart = Cart.objects.get(pk=cart_id)
        except Cart.DoesNotExist:
            continue

        for product_id, quantity in items:
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                continue

            CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity},
            )


def remove_cart_items(apps, schema_editor):
    CartItem = apps.get_model('AliceInChains', 'CartItem')
    CartItem.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('AliceInChains', '0005_order_orderitem_and_product_fixes'),
    ]

    operations = [
        migrations.RunPython(add_cart_items, remove_cart_items),
    ]
