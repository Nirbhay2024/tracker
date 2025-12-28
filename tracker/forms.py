from django import forms
from .models import Evidence

class EvidenceForm(forms.ModelForm):
    class Meta:
        model = Evidence
        fields = ['image', 'gps_lat', 'gps_long']
        widgets = {
            # Hide these inputs, we will fill them with JavaScript
            'gps_lat': forms.HiddenInput(),
            'gps_long': forms.HiddenInput(),
        }