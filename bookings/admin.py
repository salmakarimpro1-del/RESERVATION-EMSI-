from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'date', 'start_time', 'end_time', 'activity_type', 'attendees_count', 'status', 'reviewed_by')
    list_filter = ('status', 'activity_type', 'date')
    search_fields = ('room__name', 'room__code', 'user__username', 'purpose')
