from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Client(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Project(models.Model):
    # Your updated dashboard uses normalized explicit status structures
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Pending', 'Pending'),
        ('Blocked', 'Blocked'),
    ]

    name = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='projects')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    delivery_date = models.DateField()
    progress = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    description = models.TextField(blank=True, default='')
    
    # Store people as a simple JSON list to directly match your frontend data structure
    people = models.JSONField(default=list, blank=True)
    github_url = models.URLField(max_length=500, blank=True, default='')
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['delivery_date']

    def __str__(self):
        return self.name

    @property
    def normalized_status(self):
        """
        Fallback logic property if old legacy database entries 
        ('In Progress', 'Delayed', etc.) ever leak through.
        """
        val = self.status.lower() if self.status else 'pending'
        if val in ['delayed', 'blocked']:
            return 'Blocked'
        if val in ['planning', 'pending']:
            return 'Pending'
        return 'Active'
# Create your models here.
