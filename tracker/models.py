from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField

# 1. CUSTOM USER (Admins, Contractors, Clients)
class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('CONTRACTOR', 'Contractor'),
        ('CLIENT', 'Client'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CONTRACTOR')

# 2. TEMPLATES (The Workflow Definitions)
class ProjectType(models.Model):
    name = models.CharField(max_length=100) # e.g. "Solar Lights"
    
    unit_name = models.CharField(
        max_length=50, 
        default="Pole", 
        help_text="What are we installing? e.g. 'Pole', 'Gantry', 'Cabinet'"
    )
    
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class StageDefinition(models.Model):
    project_type = models.ForeignKey(ProjectType, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=100) # e.g. "Pit Excavation"
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project_type.name} - {self.name}"

# 3. PROJECTS & POLES
class Project(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    ]
    
    name = models.CharField(max_length=200)
    project_type = models.ForeignKey(ProjectType, on_delete=models.PROTECT)
    client_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NEW FIELD
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    contractors = models.ManyToManyField(
        User, 
        limit_choices_to={'role': 'CONTRACTOR'}, 
        related_name='assigned_projects',
        blank=True
    )

    def __str__(self):
        return self.name

    # Helper to calculate progress percentage
    def progress(self):
        total_poles = self.poles.count()
        if total_poles == 0: return 0
        # Count poles where all stages are done (simplest way)
        # Or you can get more complex later. For now, let's just return a placeholder or 
        # calculate based on "Is the last stage done?"
        return 0 # We will improve this logic in the template for now
    
class Pole(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='poles')
    identifier = models.CharField(max_length=50) # e.g. "Pole #1"
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project.name} - {self.identifier}"
    
    @property
    def progress_percent(self):
        # 1. Get total stages required for this project type
        total_stages = self.project.project_type.stages.count()
        
        # 2. Avoid division by zero if no stages exist
        if total_stages == 0:
            return 0
            
        # 3. Count how many unique stages have uploaded evidence
        # We import Evidence here to avoid "Circular Import" errors
        from .models import Evidence
        completed_stages = Evidence.objects.filter(pole=self).values('stage').distinct().count()
        
        # 4. Calculate percentage
        percent = (completed_stages / total_stages) * 100
        return int(percent)

# 4. EVIDENCE (Photos)
class Evidence(models.Model):
    pole = models.ForeignKey(Pole, on_delete=models.CASCADE, related_name='evidence')
    stage = models.ForeignKey(StageDefinition, on_delete=models.PROTECT)
    image = CloudinaryField('image')
    captured_at = models.DateTimeField(auto_now_add=True)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_long = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.pole.identifier} - {self.stage.name}"