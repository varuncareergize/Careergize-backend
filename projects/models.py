from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from .validators import validate_date_of_birth

class Department(models.Model):
    class Name(models.TextChoices):
        HR = 'HR', 'HR'
        IT = 'IT', 'IT'
        MARKETING = 'Marketing', 'Marketing'
        MANAGER = 'Manager', 'Manager'

    name = models.CharField(max_length=20, choices=Name.choices, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__in=['HR', 'IT', 'Marketing', 'Manager']),
                name='department_valid_name',
            ),
        ]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='user_profiles',
        null=True,
        blank=True,
    )
    phone_number = models.CharField(
        max_length=25, blank=True, default='',
        validators=[RegexValidator(
            regex=r'^\+?[0-9][0-9 ()-]{5,24}$',
            message='Enter a valid phone number, optionally including a country code.',
        )],
    )
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    postal_code = models.CharField(max_length=20, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True, validators=[validate_date_of_birth])
    bank_name = models.CharField(max_length=150, blank=True, default='')
    bank_account_holder_name = models.CharField(max_length=255, blank=True, default='')
    bank_account_number = models.CharField(max_length=50, blank=True, default='')
    bank_ifsc_code = models.CharField(max_length=11, blank=True, default='')
    bank_branch = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} profile'


class Client(models.Model):
    CLIENT_TYPE_CHOICES = [('Company', 'Company'), ('Individual', 'Individual')]
    STATUS_CHOICES = [('Lead', 'Lead'), ('Active', 'Active'), ('Inactive', 'Inactive')]

    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=25, blank=True, default='', validators=[RegexValidator(
        regex=r'^\+?[0-9][0-9 ()-]{5,24}$', message='Enter a valid phone number.',
    )])
    whatsapp_number = models.CharField(max_length=25, blank=True, default='', validators=[RegexValidator(
        regex=r'^\+?[0-9][0-9 ()-]{5,24}$', message='Enter a valid WhatsApp number.',
    )])
    address = models.TextField(blank=True, default='')
    industry = models.CharField(max_length=150, blank=True, default='')
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES, default='Company')
    source = models.CharField(max_length=150, blank=True, default='')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='assigned_clients', null=True, blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Lead')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    STATUS_CHOICES = [('Enquiry', 'Enquiry'), ('Proposal Sent', 'Proposal Sent'), ('Confirmed', 'Confirmed'), ('In Development', 'In Development'), ('Testing', 'Testing'), ('Delivered', 'Delivered'), ('Maintenance', 'Maintenance'), ('Completed', 'Completed'), ('On Hold', 'On Hold')]
    PRIORITY_CHOICES = [(value, value) for value in ['Low', 'Medium', 'High', 'Urgent']]

    name = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='projects')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    project_type = models.CharField(max_length=100, blank=True, default='')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    start_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_projects',
    )
    website_url = models.URLField(max_length=500, blank=True, default='')
    progress = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    description = models.TextField(blank=True, default='')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_projects',
        blank=True,
    )
    github_url = models.URLField(max_length=500, blank=True, default='')
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Enquiry'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expected_delivery_date']

    def __str__(self):
        return self.name

    @property
    def normalized_status(self):
        return self.status

    @property
    def amount_left(self):
        return self.total_amount - self.amount_collected
# Create your models here.

from .task_models import Task, TaskDailyUpdate, TaskComment, TaskAttachment  # noqa: E402,F401
