import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.utils.crypto import get_random_string  # <--- Essential for custom_id

class User(AbstractUser):
    ROLE_CHOICES = (('ADMIN', 'Admin'), ('CONTRACTOR', 'Contractor'))
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CONTRACTOR')

class Client(models.Model):
    name = models.CharField(max_length=200, help_text="e.g. 'UP Government' or 'Adani Power'")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class ProjectType(models.Model):
    name = models.CharField(max_length=100)
    unit_name = models.CharField(max_length=50, default="Pole")
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class StageDefinition(models.Model):
    project_type = models.ForeignKey(ProjectType, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    class Meta: ordering = ['order']
    def __str__(self): return f"{self.project_type.name} - {self.name}"

class Project(models.Model):
    STATUS_CHOICES = [('ACTIVE', 'Active'), ('COMPLETED', 'Completed')]
    name = models.CharField(max_length=200, help_text="This is the 'City' name")
    project_type = models.ForeignKey(ProjectType, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    client_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    contractors = models.ManyToManyField(User, limit_choices_to={'role': 'CONTRACTOR'}, related_name='assigned_projects', blank=True)
    data_file = models.FileField(upload_to='project_data/', blank=True, null=True, help_text="Upload CSV/Excel for dropdowns.", storage=RawMediaCloudinaryStorage())

    @property
    def has_open_issues(self):
        return self.poles.filter(issues__status='OPEN').exists()

    def __str__(self): return self.name

class ItemFieldDefinition(models.Model):
    FIELD_TYPES = (('TEXT', 'Free Text Question'), ('DROPDOWN', 'Dropdown (from File)'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='field_definitions')
    label = models.CharField(max_length=200, help_text="e.g. 'Scheme Name'")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='TEXT')
    excel_column = models.CharField(max_length=100, blank=True)
    is_grouping_key = models.BooleanField(default=False, help_text="Check this to use as the 'Village' grouping.")
    def __str__(self): return f"{self.project.name} - {self.label}"

class Pole(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='poles')
    identifier = models.CharField(max_length=100)
    
    # Unique Tracking ID (e.g. "#TRK-X92Z")
    custom_id = models.CharField(max_length=20, unique=True, blank=True, null=True, editable=False)
    
    is_completed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Auto-generate ID if not set
        if not self.custom_id:
            unique_code = get_random_string(6).upper()
            self.custom_id = f"#{unique_code}" 
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.project.name} - {self.identifier}"
    
    @property
    def progress_percent(self):
        total = self.project.project_type.stages.count()
        if total == 0: return 0
        from .models import Evidence
        done = Evidence.objects.filter(pole=self).values('stage').distinct().count()
        return int((done / total) * 100)

    @property
    def has_open_issue(self):
        return self.issues.filter(status='OPEN').exists()

class ItemFieldValue(models.Model):
    pole = models.ForeignKey(Pole, on_delete=models.CASCADE, related_name='custom_values')
    field_def = models.ForeignKey(ItemFieldDefinition, on_delete=models.CASCADE)
    value = models.CharField(max_length=500)
    def __str__(self): return f"{self.pole.identifier} - {self.value}"

class Evidence(models.Model):
    pole = models.ForeignKey(Pole, on_delete=models.CASCADE, related_name='evidence')
    stage = models.ForeignKey(StageDefinition, on_delete=models.PROTECT)
    image = CloudinaryField('image')
    captured_at = models.DateTimeField(auto_now_add=True)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_long = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    def __str__(self): return f"{self.pole.identifier} - {self.stage.name}"

class ProjectIssue(models.Model):
    STATUS_CHOICES = [('OPEN', 'Open'), ('RESOLVED', 'Resolved')]
    pole = models.ForeignKey(Pole, on_delete=models.CASCADE, related_name='issues')
    reported_by = models.CharField(max_length=100, default="Client")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Issue on {self.pole.identifier}: {self.status}"

# === NEW: PROJECT ACTIVITY LOG ===
class ProjectLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # e.g., "Created Item", "Uploaded Evidence"
    target = models.CharField(max_length=200) # e.g., "Pole #A1", "Project Settings"
    details = models.TextField(blank=True)    # Detailed info (Custom fields, changes)
    gps_lat = models.CharField(max_length=50, blank=True, null=True)
    gps_long = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.project.name} - {self.action} - {self.timestamp}"