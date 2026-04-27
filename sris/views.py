from rest_framework import permissions, viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from datetime import datetime, timedelta
from .models import AppSetting
from .serializers import AppSettingSerializer
from bookings.models import Booking
from rooms.models import Room


class AppSettingViewSet(viewsets.ModelViewSet):
    queryset = AppSetting.objects.order_by('key')
    serializer_class = AppSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['key', 'label', 'description']
    ordering_fields = ['key', 'created_at', 'updated_at']
    ordering = ['key']

    def get_permissions(self):
        """Seul les admins peuvent modifier les settings."""
        if self.action in ['list', 'retrieve', 'dashboard']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def dashboard(self, request):
        """Retourne les statistiques du système."""
        today = datetime.now().date()
        last_7_days = today - timedelta(days=7)
        
        total_bookings = Booking.objects.count()
        today_bookings = Booking.objects.filter(date=today).count()
        upcoming_bookings = Booking.objects.filter(
            date__gte=today,
            status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED],
        ).count()
        confirmed_bookings = Booking.objects.filter(status=Booking.STATUS_APPROVED).count()
        cancelled_bookings = Booking.objects.filter(status=Booking.STATUS_CANCELLED).count()
        
        # Statistiques par salle
        rooms_stats = Room.objects.annotate(
            booking_count=Count('booking')
        ).values('name', 'capacity', 'booking_count').order_by('-booking_count')
        
        # Réservations des 7 derniers jours
        recent_bookings = Booking.objects.filter(
            date__gte=last_7_days,
            date__lte=today
        ).values('date').annotate(count=Count('id')).order_by('date')
        
        return Response({
            'statistics': {
                'total_bookings': total_bookings,
                'today_bookings': today_bookings,
                'upcoming_bookings': upcoming_bookings,
                'confirmed_bookings': confirmed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'total_rooms': Room.objects.filter(is_active=True).count(),
                'active_rooms': Room.objects.filter(is_active=True).count(),
            },
            'rooms_statistics': list(rooms_stats),
            'recent_bookings': list(recent_bookings),
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def system_health(self, request):
        """Retourne l'état de santé du système."""
        from django.db import connection
        from django.db.utils import OperationalError
        
        health_status = {
            'database': 'healthy',
            'api': 'healthy',
        }
        
        # Vérifier la connexion à la base de données
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except OperationalError:
            health_status['database'] = 'unhealthy'
        
        return Response(health_status)
