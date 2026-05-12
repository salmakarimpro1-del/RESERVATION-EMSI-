from datetime import datetime

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsBookingOwnerOrStaff
from rooms.models import Room

from .models import Booking
from .serializers import BookingAvailabilitySerializer, BookingSerializer
from .utils import notify_booking_status


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('room', 'user').order_by('date', 'start_time')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsBookingOwnerOrStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'date', 'room', 'activity_type']
    search_fields = ['room__name', 'purpose', 'user__username']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.select_related('room', 'user').order_by('-created_at')
        return Booking.objects.select_related('room', 'user').filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        booking = serializer.save(user=self.request.user)
        notify_booking_created(booking)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def check_availability(self, request):
        serializer = BookingAvailabilitySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        room_id = serializer.validated_data['room']
        booking_date = serializer.validated_data['date']

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({'error': 'Salle non trouvee.'}, status=status.HTTP_404_NOT_FOUND)

        availability = Booking.objects.get_availability(room, booking_date)

        return Response(
            {
                'room': {'id': room.id, 'code': room.code, 'name': room.display_name, 'capacity': room.capacity},
                'date': booking_date,
                'availability': availability,
            }
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.user != request.user and not request.user.is_staff:
            return Response(
                {'error': "Vous n'avez pas la permission d'annuler cette reservation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status == Booking.STATUS_CANCELLED:
            return Response({'error': 'Cette reservation est deja annulee.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        notify_booking_status(booking)
        return Response({'message': 'Reservation annulee.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def confirm(self, request, pk=None):
        booking = self.get_object()

        if booking.status == Booking.STATUS_APPROVED:
            return Response({'error': 'Cette reservation est deja approuvee.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.mark_reviewed(
            reviewer=request.user,
            status=Booking.STATUS_APPROVED,
            message=request.data.get('admin_message', ''),
        )
        booking.save()
        notify_booking_status(booking)
        return Response({'message': 'Reservation approuvee.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        booking = self.get_object()

        if booking.status == Booking.STATUS_REJECTED:
            return Response({'error': 'Cette reservation est deja refusee.'}, status=status.HTTP_400_BAD_REQUEST)

        booking.mark_reviewed(
            reviewer=request.user,
            status=Booking.STATUS_REJECTED,
            message=request.data.get('admin_message', ''),
        )
        booking.save()
        notify_booking_status(booking)
        return Response({'message': 'Reservation refusee.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_bookings(self, request):
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def export_ics(self, request, pk=None):
        booking = self.get_object()
        from django.http import HttpResponse
        import uuid

        # Simple iCal content
        start_dt = datetime.combine(booking.date, booking.start_time).strftime('%Y%m%dT%H%M%S')
        end_dt = datetime.combine(booking.date, booking.end_time).strftime('%Y%m%dT%H%M%S')
        now_dt = datetime.now().strftime('%Y%m%dT%H%M%S')

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//EMSI Booking//SRIS//FR',
            'BEGIN:VEVENT',
            f'UID:{uuid.uuid4()}',
            f'DTSTAMP:{now_dt}',
            f'DTSTART:{start_dt}',
            f'DTEND:{end_dt}',
            f'SUMMARY:Reservation EMSI - {booking.room.code}',
            f'DESCRIPTION:Reservation de salle par {booking.user.full_name_or_username}. Activite: {booking.get_activity_type_display()}.',
            f'LOCATION:{booking.room.display_name} - {booking.room.building}',
            'END:VEVENT',
            'END:VCALENDAR',
        ]

        response = HttpResponse('\r\n'.join(lines), content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="reservation_{booking.id}.ics"'
        return response


