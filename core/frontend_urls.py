from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin-center/', views.admin_center_view, name='admin_center'),
    path('profile/', views.profile_view, name='profile'),
    
    # Room URLs
    path('rooms/', views.room_list_view, name='room_list'),
    path('rooms/<int:pk>/', views.room_detail_view, name='room_detail'),
    path('rooms/create/', views.room_create_view, name='room_create'),
    path('rooms/<int:pk>/update/', views.room_update_view, name='room_update'),
    path('rooms/<int:pk>/delete/', views.room_delete_view, name='room_delete'),
    
    # Booking URLs
    path('bookings/', views.booking_list_view, name='booking_list'),
    path('bookings/create/', views.booking_create_view, name='booking_create'),
    path('bookings/<int:pk>/', views.booking_detail_view, name='booking_detail'),
    path('bookings/<int:pk>/update/', views.booking_update_view, name='booking_update'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel_view, name='booking_cancel'),
    path('bookings/<int:pk>/confirm/', views.booking_confirm_view, name='booking_confirm'),
    path('bookings/<int:pk>/reject/', views.booking_reject_view, name='booking_reject'),
    path('bookings/calendar/', views.booking_calendar_view, name='booking_calendar'),
    
    # AJAX endpoints for frontend
    path('ajax/bookings/check-availability/', views.booking_availability_api, name='booking_availability_api'),
    path('ajax/bookings/calendar/', views.booking_calendar_api, name='booking_calendar_api'),
]
