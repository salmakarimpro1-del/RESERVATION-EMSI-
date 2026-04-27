from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from rooms.models import Room

from .models import Booking


User = get_user_model()


class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.room = Room.objects.create(
            building='EMSI',
            floor=2,
            code='SC999',
            name='Salle Test',
            room_type=Room.TYPE_CLASSROOM,
            capacity=10,
            location='EMSI - Etage 2',
        )
        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            date=date.today() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose='Reunion test',
        )

    def test_booking_creation(self):
        self.assertEqual(self.booking.user, self.user)
        self.assertEqual(self.booking.room, self.room)
        self.assertEqual(self.booking.status, 'EN_ATTENTE')

    def test_booking_str(self):
        expected = f'SC999 - {self.booking.date} {self.booking.start_time}-{self.booking.end_time}'
        self.assertEqual(str(self.booking), expected)

    def test_invalid_time_range(self):
        invalid_booking = Booking(
            user=self.user,
            room=self.room,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(9, 0),
            purpose='Test',
        )
        with self.assertRaises(ValidationError):
            invalid_booking.save()


class BookingViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123',
        )
        self.room = Room.objects.create(
            building='EMSI',
            floor=2,
            code='SC998',
            name='Salle Test',
            room_type=Room.TYPE_CLASSROOM,
            capacity=10,
            location='EMSI - Etage 2',
        )
        self.tomorrow = date.today() + timedelta(days=1)

    def test_booking_create_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/bookings/',
            {
                'room': self.room.id,
                'date': str(self.tomorrow),
                'start_time': '09:00',
                'end_time': '10:00',
                'purpose': 'Reunion',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)

    def test_booking_create_unauthenticated(self):
        response = self.client.post(
            '/api/bookings/',
            {
                'room': self.room.id,
                'date': str(self.tomorrow),
                'start_time': '09:00',
                'end_time': '10:00',
                'purpose': 'Reunion',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_booking_conflict_detection(self):
        Booking.objects.create(
            user=self.user,
            room=self.room,
            date=self.tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose='Reunion 1',
            status='CONFIRMEE',
        )

        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            '/api/bookings/',
            {
                'room': self.room.id,
                'date': str(self.tomorrow),
                'start_time': '09:30',
                'end_time': '10:30',
                'purpose': 'Reunion 2',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Conflit', str(response.data))

    def test_booking_user_isolation(self):
        Booking.objects.create(
            user=self.user,
            room=self.room,
            date=self.tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose='Reunion 1',
        )

        Booking.objects.create(
            user=self.other_user,
            room=self.room,
            date=self.tomorrow,
            start_time=time(11, 0),
            end_time=time(12, 0),
            purpose='Reunion 2',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/bookings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['purpose'], 'Reunion 1')

    def test_booking_cancel(self):
        booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            date=self.tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose='Reunion',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/bookings/{booking.id}/cancel/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'ANNULEE')

    def test_conflict(self):
        Booking.objects.create(
            user=self.user,
            room=self.room,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(12, 0),
            purpose='Bloc 1',
        )

        booking2 = Booking(
            user=self.user,
            room=self.room,
            date=date.today() + timedelta(days=1),
            start_time=time(11, 0),
            end_time=time(13, 0),
            purpose='Bloc 2',
        )

        with self.assertRaises(ValidationError):
            booking2.full_clean()


class BookingWebViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='salma_web',
            email='salma_web@example.com',
            password='password123',
        )
        self.staff = User.objects.create_user(
            username='admin_web',
            email='admin_web@example.com',
            password='password123',
            is_staff=True,
        )
        self.room = Room.objects.create(
            building='EMSI',
            floor=3,
            code='SCW01',
            name='Salle Web',
            room_type=Room.TYPE_CLASSROOM,
            capacity=12,
            location='EMSI - Etage 3',
        )
        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            date=date.today() + timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            purpose='Reservation web',
            status='EN_ATTENTE',
        )

    def test_booking_list_page_renders(self):
        self.client.login(username='salma_web', password='password123')
        response = self.client.get('/bookings/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reservation web')

    def test_booking_calendar_ajax_endpoint(self):
        self.client.login(username='salma_web', password='password123')
        response = self.client.get('/ajax/bookings/calendar/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['title'], 'SCW01 - Reservation web')

    def test_booking_availability_ajax_endpoint(self):
        self.client.login(username='salma_web', password='password123')
        response = self.client.get(
            '/ajax/bookings/check-availability/',
            {'room': self.room.id, 'date': self.booking.date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['bookings']), 1)
        self.assertTrue(payload['availability'])

    def test_staff_can_confirm_booking_from_web(self):
        self.client.login(username='admin_web', password='password123')
        response = self.client.post(f'/bookings/{self.booking.id}/confirm/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMEE')

    def test_admin_center_requires_staff(self):
        self.client.login(username='salma_web', password='password123')
        response = self.client.get('/admin-center/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "permission")

    def test_admin_center_bulk_approve(self):
        second_booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            date=date.today() + timedelta(days=3),
            start_time=time(10, 0),
            end_time=time(11, 0),
            purpose='Deuxieme reservation web',
            status='EN_ATTENTE',
        )

        self.client.login(username='admin_web', password='password123')
        response = self.client.post(
            '/admin-center/',
            {
                'action': 'approve',
                'booking_ids': [str(self.booking.id), str(second_booking.id)],
                'admin_message': 'Validation admin EMSI',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        second_booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMEE')
        self.assertEqual(second_booking.status, 'CONFIRMEE')
        self.assertEqual(self.booking.admin_message, 'Validation admin EMSI')
