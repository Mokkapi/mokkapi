from django import forms
import json
from .models import MokkBaseJSON

class MokkEndpointForm(forms.ModelForm):
    class Meta:
        model = MokkBaseJSON
        fields = ['path', 'data']
        help_texts = {
            'path': 'Enter the API endpoint or file path where this data should be sent.',
            'data': 'Enter valid JSON data. Format will be validated before submission.',
        }
        widgets = {
            'path': forms.TextInput(
                attrs={
                    'class': 'block w-full pr-10 border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm',
                    'placeholder': '/api/endpoint',
                }
            ),
            'data': forms.Textarea(
                attrs={
                    'class': 'block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm',
                    'rows': '8',
                    'placeholder': '{ "key": "value" }',
                }
            ),
        }
    
    def clean_data(self):
        """Validate that the data field contains valid JSON."""
        data = self.cleaned_data['data']
        if isinstance(data, dict):
            return json.dumps(data, indent=2)
        try:
            # Attempt to parse the JSON to validate it
            json_data = json.loads(data)
            # Return the formatted JSON string
            return json.dumps(json_data, indent=2)
        except json.JSONDecodeError:
            raise forms.ValidationError('Please enter valid JSON data.')
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add labels with required indicators
        self.fields['path'].label = 'Path'
        self.fields['data'].label = 'Data (JSON)'
        if 'instance' in kwargs and kwargs['instance'] is not None:
            instance = kwargs['instance']
            if hasattr(instance, 'data') and isinstance(instance.data, dict):
                self.initial['data'] = json.dumps(instance.data, indent=2)