from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0003_alter_booking_status_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='activity_type',
            field=models.CharField(
                choices=[
                    ('COURS', 'Cours'),
                    ('TP', 'Travaux pratiques'),
                    ('REUNION', 'Reunion'),
                    ('CLUB', 'Activite parascolaire'),
                    ('ATELIER', 'Atelier'),
                    ('EVENEMENT', 'Evenement'),
                ],
                default='REUNION',
                max_length=20,
                verbose_name='Type d activite',
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='admin_message',
            field=models.TextField(blank=True, verbose_name='Message de l administration'),
        ),
        migrations.AddField(
            model_name='booking',
            name='attendees_count',
            field=models.PositiveIntegerField(default=1, verbose_name='Nombre de participants'),
        ),
        migrations.AddField(
            model_name='booking',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_bookings',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(
                choices=[
                    ('EN_ATTENTE', 'En attente'),
                    ('CONFIRMEE', 'Approuvee'),
                    ('REFUSEE', 'Refusee'),
                    ('ANNULEE', 'Annulee'),
                ],
                default='EN_ATTENTE',
                max_length=20,
            ),
        ),
    ]
