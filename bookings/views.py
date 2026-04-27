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
        serializer.save(user=self.request.user)

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

        bookings = Booking.objects.filter(
            room=room,
            date=booking_date,
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED],
        ).order_by('start_time').values('start_time', 'end_time', 'user__username', 'status')

        return Response(
            {
                'room': {'id': room.id, 'code': room.code, 'name': room.display_name, 'capacity': room.capacity},
                'date': booking_date,
                'bookings': list(bookings),
                'availability': self._calculate_availability(list(bookings)),
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

    @staticmethod
    def _calculate_availability(bookings):
        available_slots = []
        busy_times = [(b['start_time'], b['end_time']) for b in bookings]
        busy_times.sort()

        from datetime import time

        current_time = time(8, 0)
        end_of_day = time(18, 0)

        for start, end in busy_times:
            if current_time < start:
                available_slots.append({'start': str(current_time), 'end': str(start)})
            current_time = max(current_time, end)

        if current_time < end_of_day:
            available_slots.append({'start': str(current_time), 'end': str(end_of_day)})

        return available_slots
