from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ProjectType, StageDefinition, Project, Pole, Evidence

# 1. Custom User Admin (This fixes the missing "Role" field)
class CustomUserAdmin(UserAdmin):
    model = User
    # This adds 'role' to the "Personal info" section in the admin
    fieldsets = UserAdmin.fieldsets + (
        ('Role Configuration', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Configuration', {'fields': ('role',)}),
    )

admin.site.register(User, CustomUserAdmin)

# 2. Template Admin (Project Types & Stages)
class StageDefinitionInline(admin.TabularInline):
    model = StageDefinition
    extra = 1

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    inlines = [StageDefinitionInline]
    list_display = ('name', 'description')

# 3. Register the other models
admin.site.register(Project)
admin.site.register(Pole)
admin.site.register(Evidence)