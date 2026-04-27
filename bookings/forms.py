from django import forms
from django.utils import timezone

from .models import Booking

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['room', 'date', 'start_time', 'end_time', 'activity_type', 'attendees_count', 'purpose']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'activity_type': forms.Select(attrs={'class': 'form-select'}),
            'attendees_count': forms.NumberInput(attrs={'type': 'number', 'min': 1, 'class': 'form-control'}),
            'purpose': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_time")
        end = cleaned_data.get("end_time")
        booking_date = cleaned_data.get("date")

        if start and end and start >= end:
            raise forms.ValidationError("L'heure de fin doit etre apres l'heure de debut.")

        if booking_date and booking_date < timezone.localdate():
            raise forms.ValidationError('La date de reservation ne peut pas etre dans le passe.')

        return cleaned_data


class BookingReviewForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['admin_message']
        widgets = {
            'admin_message': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Message interne ou retour envoye au demandeur.',
                }
            ),
        }
