from datetime import datetime

from rest_framework import serializers

from bookings.models import Booking

from .models import Room


class RoomSerializer(serializers.ModelSerializer):
    booking_count = serializers.SerializerMethodField()
    upcoming_bookings_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id',
            'building',
            'floor',
            'code',
            'name',
            'room_type',
            'capacity',
            'location',
            'description',
            'equipment',
            'is_active',
            'booking_count',
            'upcoming_bookings_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'booking_count', 'upcoming_bookings_count', 'created_at', 'updated_at']

    def get_booking_count(self, obj):
        return obj.booking_set.count()

    def get_upcoming_bookings_count(self, obj):
        today = datetime.now().date()
        return obj.booking_set.filter(date__gte=today, status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED]).count()
