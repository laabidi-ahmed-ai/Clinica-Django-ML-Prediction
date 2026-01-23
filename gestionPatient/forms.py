from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Appointment, Patient, HospitalisationStatus, MedicalHistoryEntry, Prescription, MedicalTest, Message


class BootstrapModelForm(forms.ModelForm):
    """Apply Bootstrap classes to widgets automatically."""

    bootstrap_input_class = "form-control"
    bootstrap_select_class = "form-select"
    bootstrap_textarea_class = "form-control"

    def _bootstrapify(self):
        for field in self.fields.values():
            widget = field.widget
            base_class = widget.attrs.get("class", "")
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = f"{base_class} {self.bootstrap_select_class}".strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = f"{base_class} {self.bootstrap_textarea_class}".strip()
            else:
                widget.attrs["class"] = f"{base_class} {self.bootstrap_input_class}".strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrapify()


class AppointmentPublicForm(BootstrapModelForm):
    class Meta:
        model = Appointment
        fields = [
            "name",
            "email",
            "phone",
            "requested_date",
            "requested_time",
            "department",
            "doctor_name",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your Name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Your Email"}),
            "phone": forms.TextInput(attrs={"placeholder": "Your Phone"}),
            "requested_date": forms.DateInput(attrs={"type": "date"}),
            "requested_time": forms.TimeInput(attrs={"type": "time"}),
            "department": forms.Select(),
            "doctor_name": forms.TextInput(attrs={"placeholder": "Doctor name (optional)"}),
            "notes": forms.Textarea(attrs={"placeholder": "Message (optional)", "rows": 2}),
        }

    def clean_notes(self):
        data = self.cleaned_data.get("notes", "")
        if data:
            return data.strip()
        return data

    def clean_name(self):
        name = self.cleaned_data.get("name", "")
        if name and re.search(r'\d', name):
            raise ValidationError("Name cannot contain numbers.")
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        if phone:
            # Allow only +, digits, spaces, hyphens, and parentheses
            if not re.match(r'^[\+\d\s\-\(\)]+$', phone):
                raise ValidationError("Phone number can only contain +, numbers, spaces, hyphens, and parentheses.")
            # Strip only leading/trailing spaces, but preserve the + sign
            return phone.strip()
        return phone

    def clean_requested_date(self):
        date = self.cleaned_data.get("requested_date")
        if date and date < timezone.localdate():
            raise ValidationError("Preferred date cannot be in the past.")
        return date

    def clean_requested_time(self):
        time = self.cleaned_data.get("requested_time")
        if time:
            from datetime import time as dt_time
            min_time = dt_time(8, 0)  # 8:00 AM
            max_time = dt_time(16, 59)  # 4:59 PM
            if time < min_time or time > max_time:
                raise ValidationError("Preferred time must be between 8:00 AM and 4:59 PM.")
        return time


class PatientForm(BootstrapModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "phone",
            "email",
            "address",
            "medical_history",
            "cin",
            "hospitalisation",
            "date_entree_hosp",
            "date_sortie_hosp",
            "type_hosp",
            "dossier_medical",
            "medecin_responsable",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "max": ""}),  # max will be set to today in JS
            "date_entree_hosp": forms.DateInput(attrs={"type": "date"}),
            "date_sortie_hosp": forms.DateInput(attrs={"type": "date"}),
            "phone": forms.TextInput(attrs={"pattern": r"[\+\d\s\-\(\)]+", "title": "Phone number can only contain +, numbers, spaces, hyphens, and parentheses"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "medical_history": forms.Textarea(attrs={"rows": 3}),
            "dossier_medical": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make medical_history and dossier_medical required
        self.fields["medical_history"].required = True
        self.fields["dossier_medical"].required = True
        # Update labels to English
        self.fields["date_entree_hosp"].label = "Hospital entry date"
        self.fields["date_sortie_hosp"].label = "Hospital exit date"
        self.fields["type_hosp"].label = "Hospital type"
        self.fields["dossier_medical"].label = "Medical file"
        self.fields["medecin_responsable"].label = "Responsible doctor"
        self.fields["hospitalisation"].label = "Hospitalization"

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name", "")
        if first_name and re.search(r'\d', first_name):
            raise ValidationError("First name cannot contain numbers.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name", "")
        if last_name and re.search(r'\d', last_name):
            raise ValidationError("Last name cannot contain numbers.")
        return last_name

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth and date_of_birth >= timezone.localdate():
            raise ValidationError("Date of birth must be before today.")
        return date_of_birth

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        if phone:
            # Allow only +, digits, spaces, hyphens, and parentheses
            if not re.match(r'^[\+\d\s\-\(\)]+$', phone):
                raise ValidationError("Phone number can only contain +, numbers, spaces, hyphens, and parentheses.")
            # Strip only leading/trailing spaces, but preserve the + sign
            return phone.strip()
        return phone

    def clean(self):
        cleaned_data = super().clean()
        hospitalisation = cleaned_data.get("hospitalisation")
        date_entree_hosp = cleaned_data.get("date_entree_hosp")
        date_sortie_hosp = cleaned_data.get("date_sortie_hosp")
        type_hosp = cleaned_data.get("type_hosp")

        if hospitalisation == HospitalisationStatus.YES:
            if not date_entree_hosp:
                raise ValidationError({
                    "date_entree_hosp": "Date d'entree is required when hospitalisation is 'Oui'."
                })
            if not date_sortie_hosp:
                raise ValidationError({
                    "date_sortie_hosp": "Date de sortie is required when hospitalisation is 'Oui'."
                })
            if not type_hosp:
                raise ValidationError({
                    "type_hosp": "Type d'hospitalisation is required when hospitalisation is 'Oui'."
                })
            # Validate that exit date is after entry date
            if date_entree_hosp and date_sortie_hosp and date_sortie_hosp < date_entree_hosp:
                raise ValidationError({
                    "date_sortie_hosp": "Date de sortie must be after date d'entree."
                })

        return cleaned_data


class AppointmentManageForm(BootstrapModelForm):
    patient_notes = forms.CharField(
        label="Patient's original notes",
        widget=forms.Textarea(attrs={"rows": 3, "readonly": True, "class": "form-control"}),
        required=False,
        help_text="These are the notes provided by the patient when making the appointment request."
    )
    
    # Separate field for doctor's notes (not bound to model)
    doctor_notes = forms.CharField(
        label="Doctor's Notes",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Add your notes here (these are separate from patient's notes)"}),
        required=False,
        help_text="Edit your notes here (patient's notes above will be preserved)"
    )

    class Meta:
        model = Appointment
        fields = [
            "status",
            "linked_patient",
            "price",
            "payment_status",
        ]
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Extract patient's original notes and existing doctor notes
            all_notes = self.instance.notes or ""
            if "--- Doctor's Notes ---" in all_notes:
                # Split to get patient's original notes and doctor's notes
                parts = all_notes.split("--- Doctor's Notes ---", 1)
                patient_notes_text = parts[0].strip()
                existing_doctor_notes = parts[1].strip() if len(parts) > 1 else ""
            else:
                patient_notes_text = all_notes or "No notes provided by patient."
                existing_doctor_notes = ""
            
            # Set the patient's original notes field (readonly)
            self.fields["patient_notes"].initial = patient_notes_text
            
            # Set the doctor_notes field with existing doctor notes so they can be edited
            self.fields["doctor_notes"].initial = existing_doctor_notes
            
            # Reorder fields to show patient notes first
            field_order = ["patient_notes", "status", "linked_patient", "doctor_notes", "price", "payment_status"]
            self.fields = {k: self.fields[k] for k in field_order if k in self.fields}
        
        # Add placeholder and label for price field
        self.fields["price"].label = "Appointment Fee (TND)"
        self.fields["price"].widget.attrs["placeholder"] = "100.00"


class MedicalHistoryEntryForm(BootstrapModelForm):
    """Form for creating and editing medical history entries."""
    
    class Meta:
        model = MedicalHistoryEntry
        fields = [
            "entry_date",
            "entry_type",
            "is_hospitalization",
            "hospitalization_start",
            "hospitalization_end",
            "hospitalization_type",
            "symptoms",
            "diagnosis",
            "treatment",
            "medications",
            "doctor_notes",
            "related_appointment",
        ]
        widgets = {
            "entry_date": forms.DateInput(attrs={"type": "date"}),
            "hospitalization_start": forms.DateInput(attrs={"type": "date"}),
            "hospitalization_end": forms.DateInput(attrs={"type": "date"}),
            "symptoms": forms.Textarea(attrs={"rows": 3, "placeholder": "Describe patient symptoms..."}),
            "diagnosis": forms.Textarea(attrs={"rows": 3, "placeholder": "Medical diagnosis..."}),
            "treatment": forms.Textarea(attrs={"rows": 3, "placeholder": "Treatment prescribed or performed..."}),
            "medications": forms.Textarea(attrs={"rows": 3, "placeholder": "Medications prescribed..."}),
            "doctor_notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Additional doctor notes..."}),
        }
    
    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient
        
        # Filter appointments to only show those linked to this patient
        if patient:
            self.fields["related_appointment"].queryset = Appointment.objects.filter(
                linked_patient=patient
            ).order_by("-requested_date")
        
        # Update help texts
        self.fields["is_hospitalization"].help_text = "Check if this entry includes hospitalization"
        self.fields["related_appointment"].help_text = "Link to an existing appointment (optional)"
        self.fields["entry_date"].help_text = "Date of the medical visit or hospitalization"
    
    def clean(self):
        cleaned_data = super().clean()
        is_hospitalization = cleaned_data.get("is_hospitalization")
        hospitalization_start = cleaned_data.get("hospitalization_start")
        hospitalization_end = cleaned_data.get("hospitalization_end")
        
        # If marked as hospitalization, validate dates
        if is_hospitalization:
            if not hospitalization_start:
                raise ValidationError({
                    "hospitalization_start": "Hospitalization start date is required when marking as hospitalization."
                })
            
            # Validate that end date is after start date (if provided)
            if hospitalization_start and hospitalization_end and hospitalization_end < hospitalization_start:
                raise ValidationError({
                    "hospitalization_end": "Hospitalization end date must be after start date."
                })
        
        return cleaned_data


class PrescriptionForm(BootstrapModelForm):
    """Form for adding prescriptions to an appointment."""
    
    class Meta:
        model = Prescription
        fields = [
            "medication_name",
            "dosage",
            "frequency",
            "duration",
            "instructions",
        ]
        widgets = {
            "medication_name": forms.TextInput(attrs={"placeholder": "e.g., Amoxicillin"}),
            "dosage": forms.TextInput(attrs={"placeholder": "e.g., 500mg"}),
            "frequency": forms.TextInput(attrs={"placeholder": "e.g., 3 times daily"}),
            "duration": forms.TextInput(attrs={"placeholder": "e.g., 7 days"}),
            "instructions": forms.Textarea(attrs={"rows": 2, "placeholder": "e.g., Take with food"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark instructions as optional in the UI
        self.fields["instructions"].required = False


# Create a formset for multiple prescriptions
from django.forms import inlineformset_factory

PrescriptionFormSet = inlineformset_factory(
    Appointment,  # parent model
    Prescription,  # child model
    form=PrescriptionForm,
    extra=1,  # number of empty forms to display
    can_delete=True,  # allow deletion of prescriptions
    min_num=0,  # minimum number of forms required
    validate_min=False,
)


class MedicalTestForm(BootstrapModelForm):
    """Form for requesting medical tests/analyses."""
    
    class Meta:
        model = MedicalTest
        fields = [
            "test_type",
            "test_name",
            "reason",
            "instructions",
        ]
        widgets = {
            "test_name": forms.TextInput(attrs={"placeholder": "e.g., Chest X-Ray, Complete Blood Count"}),
            "reason": forms.Textarea(attrs={"rows": 2, "placeholder": "Clinical indication for this test"}),
            "instructions": forms.Textarea(attrs={"rows": 2, "placeholder": "e.g., Fasting required for 12 hours"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructions"].required = False



class MessageForm(BootstrapModelForm):
    """Form for sending messages between doctors and patients."""
    
    class Meta:
        model = Message
        fields = [
            "subject",
            "message",
        ]
        widgets = {
            "subject": forms.TextInput(attrs={"placeholder": "Subject (optional)"}),
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Type your message here..."}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].required = False

