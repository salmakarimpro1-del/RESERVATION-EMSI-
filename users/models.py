from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_STUDENT = 'ELEVE'
    ROLE_TEACHER = 'ENSEIGNANT'
    ROLE_PROFESSOR = 'PROFESSEUR'

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Eleve'),
        (ROLE_TEACHER, 'Enseignant'),
        (ROLE_PROFESSOR, 'Professeur'),
    ]

    role = models.CharField('Role', max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    emsi_id = models.CharField('ID EMSI', max_length=30, unique=True, blank=True, null=True)
    phone = models.CharField('Telephone', max_length=30, blank=True)
    department = models.CharField('Departement', max_length=255, blank=True)

    def __str__(self):
        return self.username

    @property
    def is_admin_role(self):
        return self.is_staff or self.is_superuser

    @property
    def full_name_or_username(self):
        full_name = self.get_full_name().strip()
        return full_name or self.username

    @property
    def profile_label(self):
        role = self.get_role_display()
        return f'{role} - {self.department}' if self.department else role
