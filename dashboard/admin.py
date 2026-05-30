from django.contrib import admin

# Register your models here.
from .models import StudentProfile, Instructor, Task, Schedule

admin.site.register(StudentProfile)
admin.site.register(Instructor)
admin.site.register(Task)
admin.site.register(Schedule)