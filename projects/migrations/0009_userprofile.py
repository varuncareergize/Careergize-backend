from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import projects.validators
import django.utils.timezone


def create_existing_profiles(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Profile = apps.get_model('projects', 'UserProfile')
    alias = schema_editor.connection.alias
    for user_id in User.objects.using(alias).values_list('pk', flat=True).iterator():
        Profile.objects.using(alias).get_or_create(user_id=user_id)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0008_alter_client_id_alter_department_id_alter_project_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.RenameModel(old_name='UserDepartment', new_name='UserProfile'),
        migrations.AlterField(model_name='userprofile', name='user', field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
        migrations.AlterField(model_name='userprofile', name='department', field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_profiles', to='projects.department')),
        migrations.AddField(model_name='userprofile', name='address', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='city', field=models.CharField(max_length=100, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='state', field=models.CharField(max_length=100, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='postal_code', field=models.CharField(max_length=20, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='country', field=models.CharField(max_length=100, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='bank_name', field=models.CharField(max_length=150, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='bank_account_holder_name', field=models.CharField(max_length=255, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='bank_account_number', field=models.CharField(max_length=50, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='bank_ifsc_code', field=models.CharField(max_length=11, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='bank_branch', field=models.CharField(max_length=150, blank=True, default='')),
        migrations.AddField(model_name='userprofile', name='phone_number', field=models.CharField(max_length=25, blank=True, default='', validators=[django.core.validators.RegexValidator(regex=r'^\+?[0-9][0-9 ()-]{5,24}$', message='Enter a valid phone number, optionally including a country code.')])),
        migrations.AddField(model_name='userprofile', name='date_of_birth', field=models.DateField(null=True, blank=True, validators=[projects.validators.validate_date_of_birth])),
        migrations.AddField(model_name='userprofile', name='created_at', field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.AddField(model_name='userprofile', name='updated_at', field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.RunPython(create_existing_profiles, migrations.RunPython.noop),
    ]
