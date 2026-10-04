from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def convert_statuses(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    for old, new in {'Active': 'In Development', 'In Progress': 'In Development', 'Pending': 'Enquiry', 'Planning': 'Enquiry', 'Blocked': 'On Hold', 'Delayed': 'On Hold'}.items():
        Project.objects.using(schema_editor.connection.alias).filter(status=old).update(status=new)


class Migration(migrations.Migration):
    dependencies = [('projects', '0009_userprofile'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.RenameField(model_name='project', old_name='delivery_date', new_name='expected_delivery_date'),
        migrations.AlterField(model_name='project', name='expected_delivery_date', field=models.DateField(null=True, blank=True)),
        migrations.AlterModelOptions(name='project', options={'ordering': ['expected_delivery_date']}),
        migrations.AlterField(model_name='project', name='status', field=models.CharField(max_length=20, choices=[('Enquiry', 'Enquiry'), ('Proposal Sent', 'Proposal Sent'), ('Confirmed', 'Confirmed'), ('In Development', 'In Development'), ('Testing', 'Testing'), ('Delivered', 'Delivered'), ('Maintenance', 'Maintenance'), ('Completed', 'Completed'), ('On Hold', 'On Hold')], default='Enquiry')),
        migrations.AddField(model_name='project', name='project_type', field=models.CharField(max_length=100, blank=True, default='')),
        migrations.AddField(model_name='project', name='priority', field=models.CharField(max_length=10, choices=[(v,v) for v in ['Low','Medium','High','Urgent']], default='Medium')),
        migrations.AddField(model_name='project', name='start_date', field=models.DateField(null=True, blank=True)),
        migrations.AddField(model_name='project', name='actual_delivery_date', field=models.DateField(null=True, blank=True)),
        migrations.AddField(model_name='project', name='website_url', field=models.URLField(max_length=500, blank=True, default='')),
        migrations.AddField(model_name='project', name='project_manager', field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, related_name='managed_projects')),
        migrations.RunPython(convert_statuses, migrations.RunPython.noop),
    ]
