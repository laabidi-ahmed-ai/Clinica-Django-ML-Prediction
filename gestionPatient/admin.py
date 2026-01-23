from django.contrib import admin

from .models import Appointment, Patient, MedicalHistoryEntry, Prescription, MedicalTest, Message


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "cin",
        "hospitalisation",
        "type_hosp",
        "medecin_responsable",
        "date_derniere_mise_a_jour",
    )
    search_fields = ("first_name", "last_name", "cin", "email")
    list_filter = ("hospitalisation", "type_hosp", "medecin_responsable")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "requested_date",
        "requested_time",
        "name",
        "department",
        "status",
        "price",
        "payment_status",
        "linked_patient",
        "created_at",
    )
    search_fields = ("name", "email", "phone", "doctor_name")
    list_filter = ("department", "status", "payment_status", "requested_date")


@admin.register(MedicalHistoryEntry)
class MedicalHistoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "entry_date",
        "entry_type",
        "is_hospitalization",
        "doctor",
        "created_at",
    )
    search_fields = ("patient__first_name", "patient__last_name", "diagnosis", "doctor_notes")
    list_filter = ("entry_type", "is_hospitalization", "entry_date", "doctor")
    date_hierarchy = "entry_date"
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Patient Information", {
            "fields": ("patient", "entry_date", "entry_type", "related_appointment")
        }),
        ("Hospitalization Details", {
            "fields": ("is_hospitalization", "hospitalization_start", "hospitalization_end", "hospitalization_type"),
            "classes": ("collapse",),
        }),
        ("Medical Information", {
            "fields": ("symptoms", "diagnosis", "treatment", "medications")
        }),
        ("Doctor Information", {
            "fields": ("doctor", "doctor_notes")
        }),
        ("Metadata", {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = (
        "medication_name",
        "dosage",
        "frequency",
        "duration",
        "appointment",
        "prescribed_by",
        "created_at",
    )
    search_fields = ("medication_name", "appointment__name", "instructions")
    list_filter = ("prescribed_by", "created_at")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Medication Information", {
            "fields": ("appointment", "medication_name", "dosage", "frequency", "duration")
        }),
        ("Instructions & Details", {
            "fields": ("instructions", "prescribed_by", "created_at")
        }),
    )


@admin.register(MedicalTest)
class MedicalTestAdmin(admin.ModelAdmin):
    list_display = (
        "test_name",
        "test_type",
        "patient",
        "status",
        "requested_by",
        "requested_at",
        "scheduled_date",
    )
    search_fields = ("test_name", "patient__first_name", "patient__last_name", "reason")
    list_filter = ("test_type", "status", "requested_by", "requested_at")
    date_hierarchy = "requested_at"
    readonly_fields = ("requested_at",)
    fieldsets = (
        ("Test Information", {
            "fields": ("appointment", "patient", "test_type", "test_name", "reason")
        }),
        ("Instructions & Status", {
            "fields": ("instructions", "status", "scheduled_date", "completed_date")
        }),
        ("Results", {
            "fields": ("results", "results_file"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("requested_by", "requested_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "sender",
        "sender_type",
        "subject",
        "is_read",
        "created_at",
    )
    search_fields = ("patient__first_name", "patient__last_name", "subject", "message")
    list_filter = ("sender_type", "is_read", "created_at")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Message Information", {
            "fields": ("patient", "sender", "sender_type", "subject", "message")
        }),
        ("Status", {
            "fields": ("is_read", "parent_message", "created_at")
        }),
    )
