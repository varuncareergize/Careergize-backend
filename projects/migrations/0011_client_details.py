from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('projects', '0010_project_overview'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='client', name='contact_person', field=models.CharField(max_length=255, blank=True, default='')),
        migrations.AddField(model_name='client', name='email', field=models.EmailField(max_length=254, blank=True, default='')),
        migrations.AddField(model_name='client', name='phone', field=models.CharField(max_length=25, blank=True, default='', validators=[django.core.validators.RegexValidator(regex=r'^\+?[0-9][0-9 ()-]{5,24}$', message='Enter a valid phone number.')])),
        migrations.AddField(model_name='client', name='whatsapp_number', field=models.CharField(max_length=25, blank=True, default='', validators=[django.core.validators.RegexValidator(regex=r'^\+?[0-9][0-9 ()-]{5,24}$', message='Enter a valid WhatsApp number.')])),
        migrations.AddField(model_name='client', name='address', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='client', name='industry', field=models.CharField(max_length=150, blank=True, default='')),
        migrations.AddField(model_name='client', name='client_type', field=models.CharField(max_length=20, choices=[('Company','Company'),('Individual','Individual')], default='Company')),
        migrations.AddField(model_name='client', name='source', field=models.CharField(max_length=150, blank=True, default='')),
        migrations.AddField(model_name='client', name='assigned_to', field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_clients')),
        migrations.AddField(model_name='client', name='status', field=models.CharField(max_length=20, choices=[('Lead','Lead'),('Active','Active'),('Inactive','Inactive')], default='Lead')),
        migrations.AddField(model_name='client', name='notes', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='client', name='updated_at', field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now), preserve_default=False),
    ]
