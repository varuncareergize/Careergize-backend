# dashboard/management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from dashboard.models import StudentProfile, Instructor, Task, Schedule

class Command(BaseCommand):
    help = 'Seeds database with default details to match UI layout'

    def handle(self, *args, **kwargs):
        # Clear existing entries
        User.objects.filter(username='geethu').delete()
        Instructor.objects.all().delete()

        # Create Core User
        user = User.objects.create_user(username='geethu', first_name='Geethu', password='password123')
        
        # Build Profile Card Values
        StudentProfile.objects.create(
            user=user,
            program_name="AI/ML EXCELLENCE",
            modules_finished=12,
            total_modules=20,
            attendance_rate=92.00
        )

        # Build Instructors
        vinoba = Instructor.objects.create(name="Dr. Vinoba")
        jay = Instructor.objects.create(name="Jay")

        # Mock dynamic upcoming schedule items
        now = timezone.now()
        tomorrow_date = now + timedelta(days=1)
        june_14_date = datetime(year=2026, month=6, day=14, hour=14, minute=0, tzinfo=timezone.get_current_timezone())

        Schedule.objects.create(
            student=user,
            title="Advanced Neural Networks",
            instructor=vinoba,
            start_time=tomorrow_date.replace(hour=10, minute=0, second=0),
            end_time=tomorrow_date.replace(hour=12, minute=0, second=0)
        )

        Schedule.objects.create(
            student=user,
            title="Project: Sentiment Analysis",
            instructor=jay,
            start_time=june_14_date,
            end_time=june_14_date + timedelta(hours=2)
        )

        # Add 3 Pending Tasks to match UI notification badge count
        for i in range(3):
            Task.objects.create(student=user, title=f"Assignment Unit {i+1}", status='PENDING')

        self.stdout.write(self.style.SUCCESS('Successfully seeded dashboard environment!'))