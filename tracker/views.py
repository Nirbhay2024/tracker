from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Project
from django.contrib.auth import get_user_model  # <--- ADD THIS
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from .utils import watermark_image, get_gps_from_image
from django.contrib import messages  # <--- ADD THIS LINE

@login_required
def contractor_dashboard(request):
    # Only show projects assigned to this specific worker
    my_projects = Project.objects.filter(contractors=request.user)
    
    return render(request, 'tracker/dashboard.html', {'projects': my_projects})


from django.shortcuts import render, get_object_or_404 # <-- Add get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Project, Pole # <-- Make sure Pole is imported

# ... keep your existing contractor_dashboard view ...

@login_required
def project_detail(request, project_id):
    # 1. Get the project (or show 404 error if it doesn't exist)
    project = get_object_or_404(Project, id=project_id)
    
    # 2. Get all poles for this project
    poles = project.poles.all()
    
    return render(request, 'tracker/project_detail.html', {
        'project': project, 
        'poles': poles
    })


from django.shortcuts import redirect
from .forms import EvidenceForm # <-- Import the form we just made
from .models import Project, Pole, StageDefinition, Evidence # <-- Update imports

# ... (keep existing views) ...


@never_cache
@login_required
def dashboard(request):
    is_admin = request.user.is_superuser or request.user.is_staff

    # 1. LOGIC FOR SHOWING PROJECTS
    if is_admin:
        # Admin sees ALL projects
        projects_query = Project.objects.all().order_by('-created_at')
    else:
        # Contractors see ONLY assigned projects
        projects_query = Project.objects.filter(contractors=request.user).order_by('-created_at')
    
    # 2. Filter Active vs Completed based on the user's allowed list
    active_projects = projects_query.filter(status='ACTIVE')
    completed_projects = projects_query.filter(status='COMPLETED')

    return render(request, 'tracker/dashboard.html', {
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'is_admin': is_admin
    })

# @never_cache
# @login_required
# def dashboard(request):
#     # Only admins see the "Create" buttons and hidden features
#     is_admin = request.user.is_superuser or request.user.is_staff

#     # Get ALL projects
#     all_projects = Project.objects.all().order_by('-created_at')
    
#     # Filter them in Python or DB
#     active_projects = all_projects.filter(status='ACTIVE')
#     completed_projects = all_projects.filter(status='COMPLETED')

#     return render(request, 'tracker/dashboard.html', {
#         'active_projects': active_projects,
#         'completed_projects': completed_projects,
#         'is_admin': is_admin
#     })



from .utils import watermark_image  # <--- Make sure to import this at the top!

from .utils import watermark_image

def pole_detail(request, pole_id):
    pole = get_object_or_404(Pole, id=pole_id)
    stages = pole.project.project_type.stages.all().order_by('order')
    existing_evidence = Evidence.objects.filter(pole=pole)
    evidence_map = {e.stage.id: e for e in existing_evidence}

    if request.method == 'POST':
        # 1. Capture Data
        stage_id = request.POST.get('stage_id')
        lat = request.POST.get('gps_lat')
        lon = request.POST.get('gps_long')
        raw_file = request.FILES.get('image')

        # 2. "REPLACE" LOGIC
        if stage_id:
            stage_obj = get_object_or_404(StageDefinition, id=stage_id)
            Evidence.objects.filter(pole=pole, stage=stage_obj).delete()

        form = EvidenceForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                # 3. PREPARE INSTANCE
                evidence = form.save(commit=False)
                evidence.pole = pole
                if stage_id:
                    evidence.stage = stage_obj

                # 4. GPS FALLBACK (Check EXIF)
                if (not lat or not lon) and raw_file:
                    try:
                        if hasattr(raw_file, 'seek'): raw_file.seek(0)
                        exif_lat, exif_lon = get_gps_from_image(raw_file)
                        if exif_lat and exif_lon:
                            lat, lon = exif_lat, exif_lon
                            evidence.gps_lat, evidence.gps_long = lat, lon
                    except Exception:
                        pass # Fail silently, we just want to save the photo

                # 5. SAVE ORIGINAL
                evidence.save() 

                # 6. WATERMARK & UPDATE
                if lat and lon and raw_file:
                    try:
                        if hasattr(raw_file, 'seek'): raw_file.seek(0)
                        branded_photo = watermark_image(raw_file, lat, lon)
                        branded_photo.name = raw_file.name 
                        evidence.image = branded_photo 
                        evidence.save()
                    except Exception as e:
                        print(f"Watermark Failed: {e}")

                # ==================================================
                # 7. NEW: AUTO-COMPLETE CHECK
                # ==================================================
                # Count how many stages are REQUIRED for this project type
                required_count = StageDefinition.objects.filter(
                    project_type=pole.project.project_type, 
                    is_required=True
                ).count()
                
                # Count how many required stages HAVE EVIDENCE for this pole
                uploaded_count = Evidence.objects.filter(
                    pole=pole, 
                    stage__is_required=True
                ).values('stage').distinct().count()

                # If we have all the required photos, mark as complete!
                if uploaded_count >= required_count:
                    pole.is_completed = True
                else:
                    pole.is_completed = False # Still in progress
                
                pole.save()
                # ==================================================

                messages.success(request, "Upload successful!")
                return redirect('pole_detail', pole_id=pole.id)
            except Exception as e:
                print(f"Save Error: {e}")
                messages.error(request, f"Error saving photo: {e}")
        else:
            messages.error(request, "Upload failed. Check terminal.")

    else:
        form = EvidenceForm()

    return render(request, 'tracker/pole_detail.html', {
        'pole': pole,
        'stages': stages,
        'evidence_map': evidence_map,
        'form': form
    })


# --- ADD THIS NEW FUNCTION FOR DELETING ---

# @login_required
# def delete_evidence(request, evidence_id):
#     evidence = get_object_or_404(Evidence, id=evidence_id)
#     pole_id = evidence.pole.id
    
#     # FIX: Removed the check for 'evidence.uploaded_by' because that field 
#     # does not exist in your database model. 
#     # We now allow any logged-in user (Admin or Contractor) to delete/replace.
#     if request.user.is_authenticated:
#         evidence.delete()
        
#         # Re-check completion status
#         pole = Pole.objects.get(id=pole_id)
#         # If we delete evidence, the pole might not be complete anymore
#         # (You can add more complex logic here if needed)
#         pole.is_completed = False 
#         pole.save()
        
#     return redirect('pole_detail', pole_id=pole_id)

@login_required
def delete_evidence(request, evidence_id):
    evidence = get_object_or_404(Evidence, id=evidence_id)
    pole = evidence.pole # Get the pole before deleting
    
    if request.user.is_authenticated:
        evidence.delete()
        
        # RE-CALCULATE COMPLETION
        required_count = StageDefinition.objects.filter(
            project_type=pole.project.project_type, 
            is_required=True
        ).count()
        
        uploaded_count = Evidence.objects.filter(
            pole=pole, 
            stage__is_required=True
        ).values('stage').distinct().count()

        # Update status
        pole.is_completed = (uploaded_count >= required_count)
        pole.save()
        
    return redirect('pole_detail', pole_id=pole.id)

from django.contrib.admin.views.decorators import staff_member_required

# ... (keep your existing code above) ...

@staff_member_required
def admin_project_inspection(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    poles = project.poles.all()
    
    # Organize data: { Pole: [Photo1, Photo2, Photo3...] }
    inspection_data = {}
    
    for pole in poles:
        # Get all photos for this pole, sorted by stage order
        photos = Evidence.objects.filter(pole=pole).order_by('stage__order')
        inspection_data[pole] = photos

    return render(request, 'tracker/admin_inspection.html', {
        'project': project,
        'inspection_data': inspection_data
    })

def client_view(request, client_uuid):
    project = get_object_or_404(Project, client_uuid=client_uuid)
    poles = project.poles.all()
    
    # Calculate Progress
    total_poles = poles.count()
    completed_poles = poles.filter(is_completed=True).count()
    progress = int((completed_poles / total_poles) * 100) if total_poles > 0 else 0

    # --- THE FIX: USE A LIST INSTEAD OF A DICT ---
    pole_list = []
    for pole in poles:
        history = pole.evidence.all().order_by('stage__order')
        pole_list.append({
            'pole_obj': pole,   # We give it a clear name
            'history': history
        })
    # ---------------------------------------------

    return render(request, 'tracker/client_view.html', {
        'project': project,
        'pole_list': pole_list, # Send the list
        'progress': progress
    })

# TEMPORARY FUNCTION - DELETE AFTER USE
def create_admin_user(request):
    User = get_user_model()  # <--- This asks Django for the CORRECT user model
    
    if not User.objects.filter(username='admin').exists():
        # Create the superuser
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        return HttpResponse("SUCCESS! User: 'admin' | Password: 'admin123' created.")
    else:
        return HttpResponse("User 'admin' already exists.")
    

@login_required
def mark_project_completed(request, project_id):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=401)
    
    project = get_object_or_404(Project, id=project_id)
    project.status = 'COMPLETED'
    project.save()
    return redirect('dashboard')


@login_required
def create_project_item(request, project_id):
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        
        # 1. Get the dynamic name (e.g., "Gantry" or "Pole")
        unit_name = project.project_type.unit_name
        
        # 2. Calculate the next number safely
        # Start with (Total + 1)
        next_number = project.poles.count() + 1
        new_identifier = f"{unit_name} #{next_number}"
        
        # Safety Loop: If "Pole #5" exists (maybe #6 was deleted?), keep adding 1 until we find a free name
        while project.poles.filter(identifier=new_identifier).exists():
            next_number += 1
            new_identifier = f"{unit_name} #{next_number}"
            
        # 3. Create the new item
        # Note: We still use the 'Pole' model, but the identifier makes it look like a Gantry/etc.
        Pole.objects.create(
            project=project,
            identifier=new_identifier,
            is_completed=False
        )
        
        messages.success(request, f"New {unit_name} added: {new_identifier}")
        return redirect('project_detail', project_id=project.id)
    
    return redirect('dashboard')


