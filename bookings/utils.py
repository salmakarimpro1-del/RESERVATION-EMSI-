"""Utilitaires pour l'application de reservation de salles."""

from datetime import datetime, time as datetime_time

from django.conf import settings
from django.core.mail import send_mail

from rooms.models import Room

from .models import Booking


def get_room_availability(room_id, date):
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return None

    bookings = Booking.objects.filter(
        room=room,
        date=date,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED],
    ).order_by('start_time').values_list('start_time', 'end_time')

    available_slots = calculate_available_slots(list(bookings))

    return {
        'room': {
            'id': room.id,
            'code': room.code,
            'name': room.display_name,
            'capacity': room.capacity,
            'location': room.location,
        },
        'date': date,
        'bookings_count': len(bookings),
        'available_slots': available_slots,
    }


def calculate_available_slots(busy_times):
    work_start = datetime_time(8, 0)
    work_end = datetime_time(18, 0)

    if not busy_times:
        return [{'start': str(work_start), 'end': str(work_end)}]

    available_slots = []
    busy_times = sorted(busy_times)

    current_time = work_start

    for start, end in busy_times:
        if current_time < start:
            available_slots.append({'start': str(current_time), 'end': str(start)})
        current_time = max(current_time, end)

    if current_time < work_end:
        available_slots.append({'start': str(current_time), 'end': str(work_end)})

    return available_slots


def check_booking_conflict(room, date, start_time, end_time, exclude_id=None):
    conflicts = Booking.objects.filter(
        room=room,
        date=date,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED],
        start_time__lt=end_time,
        end_time__gt=start_time,
    )

    if exclude_id:
        conflicts = conflicts.exclude(pk=exclude_id)

    return list(conflicts)


def get_user_bookings_summary(user):
    today = datetime.now().date()

    all_bookings = Booking.objects.filter(user=user)
    upcoming = all_bookings.filter(date__gte=today).order_by('date')
    past = all_bookings.filter(date__lt=today)

    return {
        'total_bookings': all_bookings.count(),
        'upcoming_bookings': upcoming.count(),
        'past_bookings': past.count(),
        'cancelled_bookings': all_bookings.filter(status=Booking.STATUS_CANCELLED).count(),
        'confirmed_bookings': all_bookings.filter(status=Booking.STATUS_APPROVED).count(),
    }


def notify_booking_status(booking):
    if not booking.user.email:
        return

    subject = f'EMSI Booking - mise a jour de la demande {booking.room.code}'
    lines = [
        f'Bonjour {booking.user.full_name_or_username},',
        '',
        f'Votre demande de reservation pour la salle {booking.room.code} a ete mise a jour.',
        f'Statut: {booking.get_status_display()}',
        f'Date: {booking.date}',
        f'Horaires: {booking.start_time} - {booking.end_time}',
        f'Activite: {booking.get_activity_type_display()}',
    ]
    if booking.admin_message:
        lines.extend(['', "Message de l'administration:", booking.admin_message])

    send_mail(
        subject,
        '\n'.join(lines),
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        fail_silently=True,
    )
