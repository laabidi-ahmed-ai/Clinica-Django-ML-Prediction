from django.conf import settings
from django.db import models


class HospitalisationStatus(models.TextChoices):
    YES = "oui", "Yes"
    NO = "non", "No"


class HospitalisationType(models.TextChoices):
    CHIRURGIE = "chirurgie", "Surgery"
    OBSERVATION = "observation", "Observation"
    URGENCE = "urgence", "Emergency"


class AppointmentDepartment(models.TextChoices):
    HOSPITAL = "hospital", "Hospital"
    LABORATORY = "laboratoire", "Laboratoire"
    RADIOLOGY = "radiologie", "Radiologie"
    OTHER = "autre", "Autre"


class AppointmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class MedicalTestType(models.TextChoices):
    XRAY = "xray", "X-Ray"
    CT_SCAN = "ct_scan", "CT Scan"
    MRI = "mri", "MRI"
    ULTRASOUND = "ultrasound", "Ultrasound"
    BLOOD_TEST = "blood_test", "Blood Test"
    URINE_TEST = "urine_test", "Urine Test"
    ECG = "ecg", "ECG/EKG"
    ENDOSCOPY = "endoscopy", "Endoscopy"
    BIOPSY = "biopsy", "Biopsy"
    OTHER = "other", "Other"


class MedicalTestStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    medical_history = models.TextField("Medical history", blank=True, null=True)
    cin = models.CharField("CIN", max_length=20, unique=True, blank=True, null=True)
    hospitalisation = models.CharField(
        "Hospitalization",
        max_length=3,
        choices=HospitalisationStatus.choices,
        default=HospitalisationStatus.NO,
    )
    date_entree_hosp = models.DateField("Hospital entry date", blank=True, null=True)
    date_sortie_hosp = models.DateField("Hospital exit date", blank=True, null=True)
    type_hosp = models.CharField(
        "Hospital type",
        max_length=12,
        choices=HospitalisationType.choices,
        blank=True,
        null=True,
    )
    dossier_medical = models.TextField("Medical file", blank=True, null=True)
    medecin_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Responsible doctor",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="patients_suivis",
    )
    date_derniere_mise_a_jour = models.DateTimeField("Last update", auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Appointment(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    requested_date = models.DateField()
    requested_time = models.TimeField()
    department = models.CharField(
        max_length=20,
        choices=AppointmentDepartment.choices,
    )
    doctor_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.PENDING,
    )
    linked_patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="appointments",
    )
    
    # Billing fields
    price = models.DecimalField(
        "Appointment price (TND)",
        max_digits=10,
        decimal_places=2,
        default=100.00,
        help_text="Price in Tunisian Dinars"
    )
    payment_status = models.CharField(
        "Payment status",
        max_length=20,
        choices=[
            ('unpaid', 'Unpaid'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
        ],
        default='unpaid'
    )
    payment_date = models.DateTimeField("Payment date", null=True, blank=True)
    payment_method = models.CharField(
        "Payment method",
        max_length=50,
        blank=True,
        choices=[
            ('cash', 'Cash'),
            ('card', 'Credit/Debit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('online', 'Online Payment'),
        ]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Appointment {self.name} ({self.get_status_display()})"

    def get_patient_notes(self):
        """Extract patient's original notes (before doctor's notes)."""
        if not self.notes:
            return ""
        if "--- Doctor's Notes ---" in self.notes:
            return self.notes.split("--- Doctor's Notes ---")[0].strip()
        return self.notes

    def get_doctor_notes(self):
        """Extract doctor's notes if they exist."""
        if not self.notes or "--- Doctor's Notes ---" not in self.notes:
            return ""
        parts = self.notes.split("--- Doctor's Notes ---", 1)
        return parts[1].strip() if len(parts) > 1 else ""


class MedicalHistoryEntry(models.Model):
    """
    Tracks individual medical history entries for a patient.
    Records visits, hospitalizations, diagnoses, treatments, and doctor notes.
    """
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medical_history_entries",
        verbose_name="Patient"
    )
    entry_date = models.DateField("Entry date", help_text="Date of visit or hospitalization")
    entry_type = models.CharField(
        "Entry type",
        max_length=20,
        choices=[
            ('visit', 'Medical Visit'),
            ('hospitalization', 'Hospitalization'),
            ('emergency', 'Emergency'),
            ('follow_up', 'Follow-up'),
            ('surgery', 'Surgery'),
        ],
        default='visit'
    )
    
    # Hospitalization details (if applicable)
    is_hospitalization = models.BooleanField("Is hospitalization", default=False)
    hospitalization_start = models.DateField("Hospitalization start", blank=True, null=True)
    hospitalization_end = models.DateField("Hospitalization end", blank=True, null=True)
    hospitalization_type = models.CharField(
        "Hospitalization type",
        max_length=12,
        choices=HospitalisationType.choices,
        blank=True,
        null=True
    )
    
    # Medical information
    diagnosis = models.TextField("Diagnosis", blank=True, help_text="Medical diagnosis or reason for visit")
    symptoms = models.TextField("Symptoms", blank=True, help_text="Patient symptoms reported")
    treatment = models.TextField("Treatment", blank=True, help_text="Treatment prescribed or performed")
    medications = models.TextField("Medications", blank=True, help_text="Medications prescribed")
    
    # Doctor information and notes
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Attending doctor",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="medical_entries",
    )
    doctor_notes = models.TextField("Doctor notes", blank=True)
    
    # Appointment link (if this entry is related to an appointment)
    related_appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="history_entry"
    )
    
    # Metadata
    created_at = models.DateTimeField("Created at", auto_now_add=True)
    updated_at = models.DateTimeField("Last updated", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Created by",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_history_entries",
    )

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        verbose_name = "Medical History Entry"
        verbose_name_plural = "Medical History Entries"

    def __str__(self):
        return f"{self.patient} - {self.get_entry_type_display()} on {self.entry_date}"
    
    def get_duration_days(self):
        """Calculate hospitalization duration in days."""
        if self.is_hospitalization and self.hospitalization_start and self.hospitalization_end:
            delta = self.hospitalization_end - self.hospitalization_start
            return delta.days
        return None


class Prescription(models.Model):
    """
    Prescription model for medications prescribed by doctors during appointments.
    Each prescription is linked to an appointment and can contain multiple medications.
    """
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="prescriptions",
        verbose_name="Appointment"
    )
    medication_name = models.CharField("Medication name", max_length=200)
    dosage = models.CharField("Dosage", max_length=100, help_text="e.g., 500mg, 10ml")
    frequency = models.CharField(
        "Frequency",
        max_length=100,
        help_text="e.g., Once daily, Twice daily, Every 8 hours"
    )
    duration = models.CharField(
        "Duration",
        max_length=100,
        help_text="e.g., 7 days, 2 weeks, 1 month"
    )
    instructions = models.TextField(
        "Instructions",
        blank=True,
        help_text="Additional instructions (e.g., Take with food, Take before bedtime)"
    )
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Prescribed by",
        on_delete=models.SET_NULL,
        null=True,
        related_name="prescribed_medications"
    )
    created_at = models.DateTimeField("Prescribed on", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"

    def __str__(self):
        return f"{self.medication_name} - {self.dosage} ({self.frequency})"


class MedicalTest(models.Model):
    """
    Medical test/analysis request model.
    Doctors can request medical tests (X-Ray, blood tests, etc.) for patients.
    """
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="medical_tests",
        verbose_name="Appointment"
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medical_tests",
        verbose_name="Patient",
        null=True,
        blank=True
    )
    test_type = models.CharField(
        "Test type",
        max_length=50,
        choices=MedicalTestType.choices
    )
    test_name = models.CharField(
        "Test name",
        max_length=200,
        help_text="Specific name or description of the test"
    )
    reason = models.TextField(
        "Reason/Clinical indication",
        help_text="Why this test is needed"
    )
    instructions = models.TextField(
        "Instructions for patient",
        blank=True,
        help_text="e.g., Fasting required, specific preparation needed"
    )
    status = models.CharField(
        "Status",
        max_length=20,
        choices=MedicalTestStatus.choices,
        default=MedicalTestStatus.REQUESTED
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Requested by",
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_tests"
    )
    requested_at = models.DateTimeField("Requested on", auto_now_add=True)
    scheduled_date = models.DateField("Scheduled date", null=True, blank=True)
    completed_date = models.DateField("Completed date", null=True, blank=True)
    results = models.TextField("Test results", blank=True)
    results_file = models.FileField(
        "Results file",
        upload_to="medical_tests/",
        blank=True,
        null=True,
        help_text="Upload test results (PDF, image, etc.)"
    )

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "Medical test"
        verbose_name_plural = "Medical tests"

    def __str__(self):
        patient_name = self.patient or self.appointment.name
        return f"{self.test_name} for {patient_name}"


class Message(models.Model):
    """
    Messaging system between doctors and patients.
    Allows quick communication for advice and consultations.
    """
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Patient"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Sender"
    )
    sender_type = models.CharField(
        "Sender type",
        max_length=10,
        choices=[
            ('doctor', 'Doctor'),
            ('patient', 'Patient'),
        ],
        default='doctor'
    )
    subject = models.CharField("Subject", max_length=200, blank=True)
    message = models.TextField("Message")
    is_read = models.BooleanField("Read", default=False)
    created_at = models.DateTimeField("Sent at", auto_now_add=True)
    
    # For threading conversations
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="Reply to"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.sender_type.title()} to {self.patient} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])