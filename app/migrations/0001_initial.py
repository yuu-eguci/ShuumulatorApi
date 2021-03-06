# Generated by Django 3.1.7 on 2021-04-04 10:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=45, unique=True, verbose_name='銘柄コード')),
                ('name', models.CharField(max_length=45, verbose_name='銘柄名')),
            ],
            options={
                'db_table': 'stock',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=45, verbose_name='名称')),
            ],
            options={
                'db_table': 'user',
            },
        ),
        migrations.CreateModel(
            name='Trading',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('buy', models.DecimalField(decimal_places=2, max_digits=8, null=True, verbose_name='買付価格')),
                ('bought_at', models.DateTimeField(null=True, verbose_name='買付時刻')),
                ('sell', models.DecimalField(decimal_places=2, max_digits=8, null=True, verbose_name='売付価格')),
                ('sold_at', models.DateTimeField(null=True, verbose_name='売付時刻')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成時刻')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='app.stock', verbose_name='銘柄')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='app.user', verbose_name='ユーザ')),
            ],
            options={
                'db_table': 'trading',
            },
        ),
        migrations.CreateModel(
            name='StockLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='価格')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成時刻')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='app.stock', verbose_name='銘柄')),
            ],
            options={
                'db_table': 'stock_log',
            },
        ),
    ]
