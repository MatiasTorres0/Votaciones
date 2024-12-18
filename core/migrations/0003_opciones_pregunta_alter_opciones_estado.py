# Generated by Django 5.0.7 on 2024-12-16 21:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_opciones_remove_pregunta_estado_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='opciones',
            name='pregunta',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.pregunta'),
        ),
        migrations.AlterField(
            model_name='opciones',
            name='estado',
            field=models.CharField(choices=[('NOMINADO', 'Nominado'), ('GANADOR', 'Ganador')], default='NOMINADO', max_length=20),
        ),
    ]
