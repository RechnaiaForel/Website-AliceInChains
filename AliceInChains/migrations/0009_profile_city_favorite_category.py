import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AliceInChains', '0008_populate_profiles'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='city',
            field=models.CharField(blank=True, max_length=100, verbose_name='Город доставки'),
        ),
        migrations.AddField(
            model_name='profile',
            name='favorite_category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='fans',
                to='AliceInChains.category',
                verbose_name='Любимая категория',
            ),
        ),
    ]
