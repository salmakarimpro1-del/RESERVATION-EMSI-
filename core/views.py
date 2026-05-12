from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.exceptions import ValidationError

from bookings.forms import BookingForm, BookingReviewForm
from bookings.models import Booking
from bookings.utils import calculate_available_slots, notify_booking_created, notify_booking_status
from rooms.forms import RoomForm
from rooms.models import Room
from users.forms import ProfileForm, RegisterForm
from users.models import CustomUser
from django.core.mail import send_mail
from django.conf import settings


def _apply_booking_action(booking, reviewer, action, message_text=''):
    if action == 'approve':
        booking.mark_reviewed(
            reviewer=reviewer,
            status=Booking.STATUS_APPROVED,
            message=message_text,
        )
    elif action == 'reject':
        booking.mark_reviewed(
            reviewer=reviewer,
            status=Booking.STATUS_REJECTED,
            message=message_text,
        )
    elif action == 'cancel':
        booking.status = Booking.STATUS_CANCELLED
        if message_text:
            booking.admin_message = message_text
    elif action == 'pending':
        booking.status = Booking.STATUS_PENDING
        if message_text:
            booking.admin_message = message_text
    else:
        raise ValueError('Action admin inconnue.')

    booking.save()
    notify_booking_status(booking)


def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        username = identifier

        if '@' in identifier:
            matched_user = CustomUser.objects.filter(email__iexact=identifier).first()
            if matched_user:
                username = matched_user.username

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, "Identifiant ou mot de passe incorrect.")

    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.email:
                send_mail(
                    'Bienvenue sur EMSI Booking',
                    '\n'.join(
                        [
                            f'Bonjour {user.full_name_or_username},',
                            '',
                            'Votre compte EMSI Booking a ete cree avec succes.',
                            'Vous pouvez maintenant vous connecter et soumettre vos demandes de reservation.',
                        ]
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            messages.success(request, 'Compte cree avec succes. Vous pouvez maintenant vous connecter.')
            return redirect('login')
        messages.error(request, 'Merci de corriger les erreurs du formulaire.')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    scoped_bookings = Booking.objects.all() if request.user.is_staff else Booking.objects.filter(user=request.user)
    recent_bookings = scoped_bookings.select_related('room', 'user').order_by('-created_at')[:6]
    all_active_rooms = list(Room.objects.filter(is_active=True).order_by('floor', 'code'))

    room_counts = Room.objects.filter(is_active=True).values('room_type').annotate(total=Count('id')).order_by('room_type')
    room_overview = {row['room_type']: row['total'] for row in room_counts}
    floor_overview = []
    for floor in range(1, 6):
        floor_rooms = [room for room in all_active_rooms if room.floor == floor]
        floor_overview.append(
            {
                'floor': floor,
                'classrooms': [room for room in floor_rooms if room.room_type == Room.TYPE_CLASSROOM],
                'labs': [room for room in floor_rooms if room.room_type == Room.TYPE_LAB],
                'conferences': [room for room in floor_rooms if room.room_type == Room.TYPE_CONFERENCE],
            }
        )

    context = {
        'statistics': {
            'total_bookings': scoped_bookings.count(),
            'today_bookings': scoped_bookings.filter(date=today).count(),
            'upcoming_bookings': scoped_bookings.filter(
                date__gte=today,
                status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED],
            ).count(),
            'pending_bookings': scoped_bookings.filter(status=Booking.STATUS_PENDING).count(),
            'confirmed_bookings': scoped_bookings.filter(status=Booking.STATUS_APPROVED).count(),
            'rejected_bookings': scoped_bookings.filter(status=Booking.STATUS_REJECTED).count(),
            'cancelled_bookings': scoped_bookings.filter(status=Booking.STATUS_CANCELLED).count(),
            'active_rooms': Room.objects.filter(is_active=True).count(),
        },
        'recent_bookings': recent_bookings,
        'room_usage': Room.objects.filter(is_active=True).annotate(total=Count('booking')).order_by('-total', 'code')[:6],
        'pending_bookings': (
            Booking.objects.filter(status=Booking.STATUS_PENDING).select_related('room', 'user').order_by('date', 'start_time')[:5]
            if request.user.is_staff
            else []
        ),
        'room_overview': {
            'classrooms': room_overview.get(Room.TYPE_CLASSROOM, 0),
            'labs': room_overview.get(Room.TYPE_LAB, 0),
            'conferences': room_overview.get(Room.TYPE_CONFERENCE, 0),
        },
        'floor_overview': floor_overview,
    }
    return render(request, 'sris/dashboard.html', context)


@login_required
def admin_center_view(request):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission d'acceder au centre d'administration.")
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        booking_ids = request.POST.getlist('booking_ids')
        message_text = request.POST.get('admin_message', '').strip()

        if not booking_ids:
            messages.error(request, 'Selectionnez au moins une demande a traiter.')
            return redirect('admin_center')

        queryset = Booking.objects.filter(pk__in=booking_ids).select_related('room', 'user')
        processed_count = 0
        skipped_count = 0

        for booking in queryset:
            if action == 'approve' and booking.status in [Booking.STATUS_APPROVED, Booking.STATUS_CANCELLED]:
                skipped_count += 1
                continue
            if action == 'reject' and booking.status in [Booking.STATUS_REJECTED, Booking.STATUS_CANCELLED]:
                skipped_count += 1
                continue
            if action == 'cancel' and booking.status == Booking.STATUS_CANCELLED:
                skipped_count += 1
                continue
            if action == 'pending' and booking.status == Booking.STATUS_PENDING:
                skipped_count += 1
                continue

            _apply_booking_action(booking, request.user, action, message_text)
            processed_count += 1

        if processed_count:
            messages.success(request, f'{processed_count} demande(s) traitee(s) avec succes.')
        if skipped_count:
            messages.info(request, f'{skipped_count} demande(s) ignoree(s) car deja dans un statut incompatible.')
        return redirect('admin_center')

    status_filter = request.GET.get('status', Booking.STATUS_PENDING)
    role_filter = request.GET.get('role', '')
    activity_filter = request.GET.get('activity_type', '')
    floor_filter = request.GET.get('floor', '')
    search = request.GET.get('search', '').strip()

    admin_bookings = Booking.objects.select_related('room', 'user', 'reviewed_by').order_by('date', 'start_time')
    if status_filter:
        admin_bookings = admin_bookings.filter(status=status_filter)
    if role_filter:
        admin_bookings = admin_bookings.filter(user__role=role_filter)
    if activity_filter:
        admin_bookings = admin_bookings.filter(activity_type=activity_filter)
    if floor_filter:
        admin_bookings = admin_bookings.filter(room__floor=floor_filter)
    if search:
        admin_bookings = admin_bookings.filter(
            Q(room__code__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__username__icontains=search)
            | Q(purpose__icontains=search)
        )

    pending_base = Booking.objects.filter(status=Booking.STATUS_PENDING)
    approved_base = Booking.objects.filter(status=Booking.STATUS_APPROVED)
    floor_metrics = []
    for floor in range(1, 6):
        rooms_count = Room.objects.filter(is_active=True, floor=floor).count()
        pending_count = pending_base.filter(room__floor=floor).count()
        approved_count = approved_base.filter(room__floor=floor).count()
        floor_metrics.append(
            {
                'floor': floor,
                'rooms_count': rooms_count,
                'pending_count': pending_count,
                'approved_count': approved_count,
                'load_index': pending_count + approved_count,
            }
        )

    raw_role_breakdown = (
        pending_base.values('user__role')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    role_labels = dict(CustomUser.ROLE_CHOICES)
    role_breakdown = [
        {'label': role_labels.get(row['user__role'], row['user__role']), 'total': row['total']}
        for row in raw_role_breakdown
    ]

    raw_activity_breakdown = (
        Booking.objects.values('activity_type')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    activity_labels = dict(Booking.ACTIVITY_TYPE_CHOICES)
    activity_breakdown = [
        {'label': activity_labels.get(row['activity_type'], row['activity_type']), 'total': row['total']}
        for row in raw_activity_breakdown
    ]
    recent_decisions = (
        Booking.objects.exclude(status=Booking.STATUS_PENDING)
        .select_related('room', 'user', 'reviewed_by')
        .order_by('-reviewed_at', '-created_at')[:8]
    )

    paginator = Paginator(admin_bookings, 15)
    bookings_page = paginator.get_page(request.GET.get('page'))

    context = {
        'bookings': bookings_page,
        'role_choices': CustomUser.ROLE_CHOICES,
        'activity_choices': Booking.ACTIVITY_TYPE_CHOICES,
        'status_choices': Booking.STATUS_CHOICES,
        'floors': range(1, 6),
        'status_filter': status_filter,
        'role_filter': role_filter,
        'activity_filter': activity_filter,
        'floor_filter': floor_filter,
        'search': search,
        'review_form': BookingReviewForm(),
        'summary': {
            'pending': pending_base.count(),
            'approved': approved_base.count(),
            'rejected': Booking.objects.filter(status=Booking.STATUS_REJECTED).count(),
            'cancelled': Booking.objects.filter(status=Booking.STATUS_CANCELLED).count(),
        },
        'floor_metrics': floor_metrics,
        'role_breakdown': role_breakdown,
        'activity_breakdown': activity_breakdown,
        'recent_decisions': recent_decisions,
    }
    return render(request, 'sris/admin_center.html', context)


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis a jour avec succes.')
            return redirect('profile')
        messages.error(request, 'Merci de corriger les erreurs du formulaire.')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'registration/profile.html', {'form': form, 'user_obj': request.user})


@login_required
def room_list_view(request):
    rooms_queryset = Room.objects.filter(is_active=True)
    capacity = request.GET.get('capacity')
    search = request.GET.get('search')
    equipment = request.GET.get('equipment')
    floor = request.GET.get('floor')
    room_type = request.GET.get('room_type')

    if capacity:
        try:
            rooms_queryset = rooms_queryset.filter(capacity__gte=int(capacity))
        except ValueError:
            messages.error(request, 'Capacite invalide.')

    if search:
        rooms_queryset = rooms_queryset.filter(
            Q(code__icontains=search)
            | Q(name__icontains=search)
            | Q(location__icontains=search)
            | Q(description__icontains=search)
        )

    if equipment:
        rooms_queryset = rooms_queryset.filter(equipment__icontains=equipment)

    if floor:
        try:
            rooms_queryset = rooms_queryset.filter(floor=int(floor))
        except ValueError:
            messages.error(request, 'Etage invalide.')

    if room_type:
        rooms_queryset = rooms_queryset.filter(room_type=room_type)

    filtered_rooms = list(rooms_queryset.order_by('floor', 'code'))
    floors_summary = []
    for level in range(1, 6):
        floor_rooms = [room for room in filtered_rooms if room.floor == level]
        if not floor_rooms:
            continue
        floors_summary.append(
            {
                'floor': level,
                'rooms_count': len(floor_rooms),
                'classrooms_count': len([room for room in floor_rooms if room.room_type == Room.TYPE_CLASSROOM]),
                'labs_count': len([room for room in floor_rooms if room.room_type == Room.TYPE_LAB]),
                'conferences_count': len([room for room in floor_rooms if room.room_type == Room.TYPE_CONFERENCE]),
                'rooms': floor_rooms,
            }
        )

    paginator = Paginator(filtered_rooms, 12)
    page_number = request.GET.get('page')
    rooms = paginator.get_page(page_number)

    return render(
        request,
        'rooms/room_list.html',
        {
            'rooms': rooms,
            'room_type_choices': Room.ROOM_TYPE_CHOICES,
            'floors': range(1, 6),
            'floors_summary': floors_summary,
        },
    )


@login_required
def room_detail_view(request, pk):
    room = get_object_or_404(Room, pk=pk)
    bookings = Booking.objects.filter(room=room, date__gte=timezone.localdate()).select_related('user').order_by('date', 'start_time')[:12]
    same_floor_rooms = (
        Room.objects.filter(is_active=True, floor=room.floor)
        .exclude(pk=room.pk)
        .order_by('code')[:6]
    )
    return render(
        request,
        'rooms/room_detail.html',
        {'room': room, 'bookings': bookings, 'same_floor_rooms': same_floor_rooms},
    )


@login_required
def room_create_view(request):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission d'acceder a cette page.")
        return redirect('room_list')

    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salle creee avec succes.')
            return redirect('room_list')
        messages.error(request, 'Merci de corriger les erreurs du formulaire.')
    else:
        form = RoomForm()

    return render(request, 'rooms/room_form.html', {'form': form})


@login_required
def room_update_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission d'acceder a cette page.")
        return redirect('room_list')

    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salle mise a jour avec succes.')
            return redirect('room_detail', pk=room.pk)
        messages.error(request, 'Merci de corriger les erreurs du formulaire.')
    else:
        form = RoomForm(instance=room)

    return render(request, 'rooms/room_form.html', {'form': form, 'room': room})


@login_required
def room_delete_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission d'acceder a cette page.")
        return redirect('room_list')

    room = get_object_or_404(Room, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'La suppression doit etre confirmee.')
        return redirect('room_detail', pk=room.pk)

    room.delete()
    messages.success(request, 'Salle supprimee avec succes.')
    return redirect('room_list')


@login_required
def booking_list_view(request):
    bookings = Booking.objects.all() if request.user.is_staff else Booking.objects.filter(user=request.user)
    status = request.GET.get('status')
    booking_date = request.GET.get('date')
    room_id = request.GET.get('room')

    if status:
        bookings = bookings.filter(status=status)
    if booking_date:
        bookings = bookings.filter(date=booking_date)
    if room_id:
        bookings = bookings.filter(room_id=room_id)

    bookings = bookings.select_related('room', 'user').order_by('-created_at')
    paginator = Paginator(bookings, 12)
    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)

    rooms = Room.objects.filter(is_active=True).order_by('floor', 'code')
    return render(request, 'bookings/booking_list.html', {'bookings': bookings, 'rooms': rooms})


@login_required
def booking_create_view(request):
    rooms = Room.objects.filter(is_active=True).order_by('floor', 'code')
    today = timezone.localdate().strftime('%Y-%m-%d')

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            try:
                booking.save()
                notify_booking_created(booking)
                messages.success(request, 'Reservation creee avec succes.')
                return redirect('booking_list')
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}" if field != '__all__' else error)
                else:
                    for error in e.messages:
                        messages.error(request, error)
            except Exception as exc:
                messages.error(request, f"Erreur lors de l'enregistrement : {str(exc)}")
        else:
            # Add specific field errors to messages if not visible
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
            messages.error(request, 'Merci de corriger les erreurs du formulaire.')
    else:
        initial_data = {}
        if request.GET.get('date'):
            initial_data['date'] = request.GET.get('date')
        if request.GET.get('start'):
            initial_data['start_time'] = request.GET.get('start')
        if request.GET.get('end'):
            initial_data['end_time'] = request.GET.get('end')
        if request.GET.get('room'):
            initial_data['room'] = request.GET.get('room')
        form = BookingForm(initial=initial_data)

    return render(request, 'bookings/booking_form.html', {'form': form, 'rooms': rooms, 'today': today})


@login_required
def booking_detail_view(request, pk):
    booking = get_object_or_404(Booking.objects.select_related('room', 'user'), pk=pk)
    if booking.user != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission de voir cette reservation.")
        return redirect('booking_list')
    review_form = BookingReviewForm(instance=booking) if request.user.is_staff else None
    return render(request, 'bookings/booking_detail.html', {'booking': booking, 'review_form': review_form})


@login_required
def booking_update_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.user != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission de modifier cette reservation.")
        return redirect('booking_list')

    if booking.status == Booking.STATUS_CANCELLED:
        messages.error(request, 'Impossible de modifier une reservation annulee.')
        return redirect('booking_list')

    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Reservation mise a jour avec succes.')
                return redirect('booking_list')
            except Exception as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, 'Merci de corriger les erreurs du formulaire.')
    else:
        form = BookingForm(instance=booking)

    rooms = Room.objects.filter(is_active=True).order_by('floor', 'code')
    return render(request, 'bookings/booking_form.html', {'form': form, 'rooms': rooms, 'booking': booking})


@login_required
def booking_cancel_view(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.user != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission d'annuler cette reservation.")
        return redirect('booking_list')

    if booking.status == Booking.STATUS_CANCELLED:
        messages.error(request, 'Cette reservation est deja annulee.')
        return redirect('booking_list')

    if request.method != 'POST':
        messages.error(request, "L'annulation doit etre confirmee.")
        return redirect('booking_list')

    _apply_booking_action(booking, request.user, 'cancel')
    messages.success(request, 'Reservation annulee avec succes.')
    return redirect('booking_list')


@login_required
def booking_confirm_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission de confirmer cette reservation.")
        return redirect('booking_list')

    booking = get_object_or_404(Booking, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'La confirmation doit etre envoyee via le formulaire.')
        return redirect('booking_list')

    if booking.status == Booking.STATUS_APPROVED:
        messages.info(request, 'Cette reservation est deja confirmee.')
        return redirect('booking_list')

    if booking.status == Booking.STATUS_CANCELLED:
        messages.error(request, 'Impossible de confirmer une reservation annulee.')
        return redirect('booking_list')

    admin_message = request.POST.get('admin_message', '').strip()
    _apply_booking_action(booking, request.user, 'approve', admin_message)
    messages.success(request, 'Reservation confirmee avec succes.')
    return redirect('booking_list')


@login_required
def booking_reject_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission de refuser cette reservation.")
        return redirect('booking_list')

    booking = get_object_or_404(Booking, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'Le refus doit etre envoye via le formulaire.')
        return redirect('booking_detail', pk=booking.pk)

    if booking.status == Booking.STATUS_REJECTED:
        messages.info(request, 'Cette reservation est deja refusee.')
        return redirect('booking_detail', pk=booking.pk)

    if booking.status == Booking.STATUS_CANCELLED:
        messages.error(request, 'Impossible de refuser une reservation annulee.')
        return redirect('booking_detail', pk=booking.pk)

    admin_message = request.POST.get('admin_message', '').strip()
    _apply_booking_action(booking, request.user, 'reject', admin_message)
    messages.success(request, 'Reservation refusee et notification preparee.')
    return redirect('booking_list')


@login_required
def booking_pending_view(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission de modifier cette reservation.")
        return redirect('booking_list')

    booking = get_object_or_404(Booking, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'L action doit etre envoyee via le formulaire.')
        return redirect('booking_detail', pk=booking.pk)

    if booking.status == Booking.STATUS_PENDING:
        messages.info(request, 'Cette reservation est deja en attente.')
        return redirect('booking_detail', pk=booking.pk)

    admin_message = request.POST.get('admin_message', '').strip()
    _apply_booking_action(booking, request.user, 'pending', admin_message)
    messages.success(request, 'Reservation remise en attente.')
    return redirect('booking_list')


@login_required
def booking_calendar_view(request):
    rooms = Room.objects.filter(is_active=True).order_by('floor', 'code')
    return render(request, 'bookings/calendar.html', {'rooms': rooms})


@login_required
def booking_availability_api(request):
    room_id = request.GET.get('room')
    booking_date = request.GET.get('date')

    if not room_id or not booking_date:
        return JsonResponse({'error': 'Parametres manquants'}, status=400)

    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Salle non trouvee'}, status=404)

    bookings = Booking.objects.filter(
        room=room,
        date=booking_date,
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED],
    ).order_by('start_time').values('start_time', 'end_time', 'user__username', 'status')

    busy_times = [(booking['start_time'], booking['end_time']) for booking in bookings]
    return JsonResponse(
        {
            'room': {
                'id': room.id,
                'code': room.code,
                'name': room.display_name,
                'capacity': room.capacity,
                'room_type': room.get_room_type_display(),
            },
            'date': booking_date,
            'bookings': list(bookings),
            'availability': calculate_available_slots(busy_times),
        }
    )


@login_required
def booking_calendar_api(request):
    room_id = request.GET.get('room')
    status = request.GET.get('status')

    bookings = Booking.objects.filter(status__in=[Booking.STATUS_PENDING, Booking.STATUS_APPROVED]).select_related('room', 'user')

    if room_id:
        bookings = bookings.filter(room_id=room_id)
    if status:
        bookings = bookings.filter(status=status)

    events = []
    for booking in bookings.order_by('date', 'start_time'):
        start_value = datetime.combine(booking.date, booking.start_time).isoformat()
        end_value = datetime.combine(booking.date, booking.end_time).isoformat()
        title = f'{booking.room.code} - {booking.purpose}'
        events.append(
            {
                'id': booking.id,
                'title': title,
                'start': start_value,
                'end': end_value,
                'status': booking.status,
                'room_name': booking.room.display_name,
                'room_code': booking.room.code,
                'user_name': booking.user.full_name_or_username,
                'purpose': booking.purpose,
            }
        )

    return JsonResponse(events, safe=False)
