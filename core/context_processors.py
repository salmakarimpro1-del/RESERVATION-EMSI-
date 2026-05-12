import os


def branding(request):
    from bookings.models import Booking
    google_enabled = bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'))
    
    pending_count = 0
    if request.user.is_authenticated and request.user.is_staff:
        pending_count = Booking.objects.filter(status='EN_ATTENTE').count()
        
    return {
        'platform_name': 'EMSI Réservation de Salles',
        'platform_short_name': 'EMSI Réservation',
        'google_oauth_enabled': google_enabled,
        'pending_bookings_count': pending_count,
    }
