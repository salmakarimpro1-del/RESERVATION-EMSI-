from datetime import date as date_cls

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from rooms.models import Room


class Booking(models.Model):
    STATUS_PENDING = 'EN_ATTENTE'
    STATUS_APPROVED = 'CONFIRMEE'
    STATUS_REJECTED = 'REFUSEE'
    STATUS_CANCELLED = 'ANNULEE'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_APPROVED, 'Approuvee'),
        (STATUS_REJECTED, 'Refusee'),
        (STATUS_CANCELLED, 'Annulee'),
    ]

    ACTIVITY_CLASS = 'COURS'
    ACTIVITY_PRACTICAL = 'TP'
    ACTIVITY_MEETING = 'REUNION'
    ACTIVITY_CLUB = 'CLUB'
    ACTIVITY_WORKSHOP = 'ATELIER'
    ACTIVITY_EVENT = 'EVENEMENT'

    ACTIVITY_TYPE_CHOICES = [
        (ACTIVITY_CLASS, 'Cours'),
        (ACTIVITY_PRACTICAL, 'Travaux pratiques'),
        (ACTIVITY_MEETING, 'Reunion'),
        (ACTIVITY_CLUB, 'Activite parascolaire'),
        (ACTIVITY_WORKSHOP, 'Atelier'),
        (ACTIVITY_EVENT, 'Evenement'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    activity_type = models.CharField(
        'Type d activite',
        max_length=20,
        choices=ACTIVITY_TYPE_CHOICES,
        default=ACTIVITY_MEETING,
    )
    attendees_count = models.PositiveIntegerField('Nombre de participants', default=1)
    purpose = models.CharField(max_length=255)
    admin_message = models.TextField('Message de l administration', blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_bookings',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'date', 'start_time'],
                name='unique_room_date_start_time',
            )
        ]
        indexes = [
            models.Index(fields=['room', 'date']),
            models.Index(fields=['user', 'date']),
        ]

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("L'heure de fin doit etre apres l'heure de debut.")

        if self.date and self.date < date_cls.today():
            raise ValidationError('La date de reservation ne peut pas etre dans le passe.')

        if not self.room_id or not self.date:
            return

        if self.attendees_count < 1:
            raise ValidationError('Le nombre de participants doit etre superieur a zero.')

        if self.room.capacity and self.attendees_count > self.room.capacity:
            raise ValidationError('Le nombre de participants depasse la capacite de la salle.')

        conflicts = Booking.objects.filter(
            room=self.room,
            date=self.date,
            status__in=[self.STATUS_PENDING, self.STATUS_APPROVED],
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        )

        if self.pk:
            conflicts = conflicts.exclude(pk=self.pk)

        if conflicts.exists():
            raise ValidationError('Conflit detecte : cette salle est deja reservee sur ce creneau.')

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.room} - {self.date} {self.start_time}-{self.end_time}'

    def mark_reviewed(self, reviewer, status, message=''):
        self.status = status
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        if message:
            self.admin_message = message
