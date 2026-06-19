from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('AliceInChains', 'Profile')

    for user in User.objects.all():
        Profile.objects.get_or_create(user=user)


def reverse_noop(apps, schema_editor):
    # Откатывать удаление профилей не требуется — модель Profile
    # всё равно удаляется при откате предыдущей миграции.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('AliceInChains', '0007_profile'),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, reverse_noop),
    ]
