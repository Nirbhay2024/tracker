from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ProjectType, StageDefinition, Project, Pole, Evidence

# 1. CUSTOM USER ADMIN
# This ensures you can see and edit the 'Role' field in the Admin Panel
class CustomUserAdmin(UserAdmin):
    model = User
    # Add 'role' to the editable fields in the admin
    fieldsets = UserAdmin.fieldsets + (
        ('Role Configuration', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Configuration', {'fields': ('role',)}),
    )

admin.site.register(User, CustomUserAdmin)


# 2. PROJECT TYPE & STAGES ADMIN
# This allows you to add Stages (e.g., Excavation, Installation) directly inside the Project Type screen
class StageDefinitionInline(admin.TabularInline):
    model = StageDefinition
    extra = 1

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_name', 'description')
    inlines = [StageDefinitionInline]


# 3. PROJECT ADMIN
# This is where we added the Contractor Selection Box
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_type', 'status', 'created_at')
    list_filter = ('status', 'project_type')
    
    # This creates the nice select box for multiple contractors
    filter_horizontal = ('contractors',) 
    
    fieldsets = (
        (None, {
            'fields': ('name', 'project_type', 'status')
        }),
        ('Assignments', {
            'fields': ('contractors',)
        }),
    )


# 4. OTHER MODELS
# Simple registration for the remaining models
admin.site.register(Pole)
admin.site.register(Evidence)

# NOTE: StageDefinition is already managed inside ProjectType, 
# but we can register it separately too if you want to see the full list.
admin.site.register(StageDefinition)