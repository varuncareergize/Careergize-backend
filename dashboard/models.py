from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    program_name = models.CharField(
        max_length=100,
        default="AI/ML Excellence"
    )

    modules_finished = models.IntegerField(default=0)
    total_modules = models.IntegerField(default=20)

    attendance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return self.user.username


class Task(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks"
    )

    title = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    due_date = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title


class Instructor(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Schedule(models.Model):

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="schedules"
    )

    title = models.CharField(max_length=255)

    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    meeting_link = models.URLField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title