from django.db import models


class Room(models.Model):
    TYPE_CLASSROOM = 'CLASSROOM'
    TYPE_LAB = 'LAB'
    TYPE_CONFERENCE = 'CONFERENCE'

    ROOM_TYPE_CHOICES = [
        (TYPE_CLASSROOM, 'Salle de cours'),
        (TYPE_LAB, 'Laboratoire informatique'),
        (TYPE_CONFERENCE, 'Salle de conference'),
    ]

    building = models.CharField(max_length=100, default='EMSI')
    floor = models.PositiveSmallIntegerField(default=1)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default=TYPE_CLASSROOM)
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    equipment = models.TextField(
        'Equipements',
        blank=True,
        help_text='Liste des equipements disponibles (ex: projecteur, tableau, wifi)',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['floor', 'code']

    def __str__(self):
        return self.code

    @property
    def equipment_items(self):
        return [item.strip() for item in self.equipment.split(',') if item.strip()]

    @property
    def display_name(self):
        return self.name or self.code

    @property
    def floor_label(self):
        if self.room_type == self.TYPE_CONFERENCE:
            return f'Etage {self.floor} - Conference'
        return f'Etage {self.floor}'

    @property
    def room_family(self):
        if self.room_type == self.TYPE_CLASSROOM:
            return 'SC'
        if self.room_type == self.TYPE_LAB:
            return 'LI'
        return 'CONF'
