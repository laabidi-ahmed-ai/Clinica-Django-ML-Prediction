from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from django.utils.decorators import method_decorator
from UserApp.decorators import role_required
from .forms import AppointmentManageForm, AppointmentPublicForm, PatientForm, PrescriptionFormSet, MedicalTestForm, MessageForm
from .models import Appointment, AppointmentStatus, Patient, AppointmentDepartment, MedicalHistoryEntry, MedicalTest, Prescription, Message
from django.db.models import Q
from itertools import chain
from operator import attrgetter


class PatientListView(ListView):
    model = Patient
    template_name = "Back/Patient/patient_list.html"
    context_object_name = "patients"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.GET.get("name")
        if name:
            queryset = queryset.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )
        return queryset.order_by("last_name", "first_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_patients"] = Patient.objects.count()
        context["current_name"] = self.request.GET.get("name", "")
        return context


class PatientDetailView(DetailView):
    model = Patient
    template_name = "Back/Patient/patient_detail.html"
    context_object_name = "patient"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Explicitly fetch all appointments for this patient ordered by date
        context['all_appointments'] = self.object.appointments.all().order_by('-requested_date')
        return context


class PatientCreateView(CreateView):
    model = Patient
    form_class = PatientForm
    template_name = "Back/Patient/patient_form.html"
    success_url = reverse_lazy("patient_list")

    def get_initial(self):
        initial = super().get_initial()
        full_name = self.request.GET.get("name")
        if full_name:
            parts = full_name.strip().split(" ", 1)
            initial["first_name"] = parts[0]
            if len(parts) > 1:
                initial["last_name"] = parts[1]
        if email := self.request.GET.get("email"):
            initial["email"] = email
        if phone := self.request.GET.get("phone"):
            initial["phone"] = phone
        return initial


class PatientUpdateView(UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = "Back/Patient/patient_form.html"
    success_url = reverse_lazy("patient_list")


class PatientDeleteView(DeleteView):
    model = Patient
    template_name = "Back/Patient/patient_confirm_delete.html"
    success_url = reverse_lazy("patient_list")


class AppointmentCreateView(CreateView):
    model = Appointment
    form_class = AppointmentPublicForm
    template_name = "Back/Patient/appointment_form.html"
    success_url = reverse_lazy("appointment_list")


class AppointmentSuccessView(TemplateView):
    template_name = "Back/Patient/appointment_success.html"


class LandingPageView(TemplateView):
    template_name = "Front/Patient/index.html"

@method_decorator(
    role_required('user', 'patient'),
    name='dispatch'
)
class PublicAppointmentCreateView(AppointmentCreateView):
    template_name = "Front/Patient/appointment_page.html"
    success_url = reverse_lazy("public_appointment")

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}?success=1"

    def form_valid(self, form):
        messages.success(self.request, "Appointment request submitted.")
        return super().form_valid(form)


class AppointmentListView(ListView):
    model = Appointment
    template_name = "Back/Patient/appointment_list.html"
    context_object_name = "appointments"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get("status")
        if status in dict(AppointmentStatus.choices):
            queryset = queryset.filter(status=status)
        linked = self.request.GET.get("linked")
        if linked:
            queryset = queryset.filter(linked_patient_id=linked)
        department = self.request.GET.get("department")
        if department in dict(AppointmentDepartment.choices):
            queryset = queryset.filter(department=department)
        name = self.request.GET.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        doctor = self.request.GET.get("doctor")
        if doctor:
            queryset = queryset.filter(doctor_name__icontains=doctor)

        # Date sorting only
        date_sort = self.request.GET.get("date_sort", "none")
        if date_sort == "asc":
            queryset = queryset.select_related("linked_patient").order_by("requested_date")
        elif date_sort == "desc":
            queryset = queryset.select_related("linked_patient").order_by("-requested_date")
        else:
            queryset = queryset.select_related("linked_patient").order_by("-created_at")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = AppointmentStatus.choices
        context["current_status"] = self.request.GET.get("status", "")
        context["department_choices"] = AppointmentDepartment.choices
        context["current_department"] = self.request.GET.get("department", "")
        context["current_name"] = self.request.GET.get("name", "")
        context["current_doctor"] = self.request.GET.get("doctor", "")
        context["current_linked"] = self.request.GET.get("linked", "")
        context["current_date_sort"] = self.request.GET.get("date_sort", "none")
        return context


class AppointmentDetailView(DetailView):
    model = Appointment
    template_name = "Back/Patient/appointment_detail.html"
    context_object_name = "appointment"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add medical test form and existing tests
        context['medical_test_form'] = MedicalTestForm()
        context['medical_tests'] = self.object.medical_tests.all()
        context['prescriptions'] = self.object.prescriptions.all()
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle medical test request form submission."""
        self.object = self.get_object()
        form = MedicalTestForm(request.POST)
        
        if form.is_valid():
            medical_test = form.save(commit=False)
            medical_test.appointment = self.object
            medical_test.patient = self.object.linked_patient
            medical_test.requested_by = request.user
            medical_test.save()
            
            messages.success(request, f"Medical test '{medical_test.test_name}' has been requested successfully.")
            return redirect('appointment_detail', pk=self.object.pk)
        else:
            context = self.get_context_data()
            context['medical_test_form'] = form
            return self.render_to_response(context)


class AppointmentUpdateView(UpdateView):
    model = Appointment
    template_name = "Back/Patient/appointment_manage_form.html"
    form_class = AppointmentManageForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['prescription_formset'] = PrescriptionFormSet(self.request.POST, instance=self.object)
        else:
            context['prescription_formset'] = PrescriptionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        prescription_formset = context['prescription_formset']
        
        # Get the ORIGINAL appointment from database (before form changes)
        original_appointment = Appointment.objects.get(pk=self.object.pk)
        all_notes = original_appointment.notes or ""
        
        # Extract patient's original notes (everything before the doctor's notes marker)
        if "--- Doctor's Notes ---" in all_notes:
            patient_original_notes = all_notes.split("--- Doctor's Notes ---")[0].strip()
        else:
            # If no marker exists, all notes are patient notes
            patient_original_notes = all_notes
        
        # Get doctor's new notes from the form's doctor_notes field (not the model's notes field)
        doctor_notes = form.cleaned_data.get("doctor_notes", "").strip()
        
        # Always preserve patient's original notes and combine with doctor's notes
        if doctor_notes:
            # Combine patient notes with doctor notes
            if patient_original_notes:
                form.instance.notes = f"{patient_original_notes}\n\n--- Doctor's Notes ---\n{doctor_notes}"
            else:
                form.instance.notes = f"--- Doctor's Notes ---\n{doctor_notes}"
        else:
            # If no doctor notes provided, keep only patient's notes
            form.instance.notes = patient_original_notes
        
        # Validate prescription formset
        if prescription_formset.is_valid():
            self.object = form.save()
            # Save prescriptions and set prescribed_by field
            prescriptions = prescription_formset.save(commit=False)
            for prescription in prescriptions:
                prescription.prescribed_by = self.request.user
                prescription.save()
            # Handle deletions
            for obj in prescription_formset.deleted_objects:
                obj.delete()
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("appointment_detail", kwargs={"pk": self.object.pk})


class DashboardHomeView(TemplateView):
    template_name = "Back/Patient/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        context["total_patients"] = Patient.objects.count()
        context["pending_appointments"] = Appointment.objects.filter(status=AppointmentStatus.PENDING).count()
        context["upcoming_today"] = Appointment.objects.filter(
            requested_date=today,
            status__in=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
        ).count()
        total_appointments = Appointment.objects.count()
        linked_count = Appointment.objects.exclude(linked_patient__isnull=True).count()
        context["linked_ratio"] = int(round((linked_count / total_appointments) * 100)) if total_appointments else 0
        context["recent_appointments"] = (
            Appointment.objects.select_related("linked_patient").order_by("-created_at")[:5]
        )
        context["latest_pending"] = (
            Appointment.objects.filter(status=AppointmentStatus.PENDING).order_by("-created_at").first()
        )
        context["recent_patients"] = Patient.objects.order_by("-date_derniere_mise_a_jour", "-id")[:5]
        return context


class PatientMedicalHistoryView(DetailView):
    """
    Display complete medical history timeline for a patient including:
    - All medical history entries
    - All appointments (completed, pending, cancelled)
    - Hospitalization records
    """
    model = Patient
    template_name = "Back/Patient/patient_medical_history.html"
    context_object_name = "patient"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object
        
        # Get all medical history entries
        history_entries = patient.medical_history_entries.select_related(
            'doctor', 'related_appointment'
        ).all()
        
        # Get all appointments
        appointments = patient.appointments.all()
        
        # Create a unified timeline by combining history entries and appointments
        # We'll display them in chronological order
        timeline_items = []
        
        # Add medical history entries to timeline
        for entry in history_entries:
            timeline_items.append({
                'type': 'history_entry',
                'date': entry.entry_date,
                'object': entry,
                'sort_date': entry.entry_date,
            })
        
        # Add all appointments to timeline
        for appointment in appointments:
            timeline_items.append({
                'type': 'appointment',
                'date': appointment.requested_date,
                'object': appointment,
                'sort_date': appointment.requested_date,
            })
        
        # Sort timeline by date (most recent first)
        timeline_items.sort(key=lambda x: x['sort_date'], reverse=True)
        
        context['timeline_items'] = timeline_items
        context['total_entries'] = len(history_entries)
        context['total_appointments'] = len(appointments)
        context['hospitalization_count'] = history_entries.filter(is_hospitalization=True).count()
        
        return context


class MyPatientPortalView(TemplateView):
    """
    Public-facing portal for logged-in patients to see their information.
    Includes medical history, appointments, and other patient services.
    This finds the patient record based on the logged-in user's email.
    """
    template_name = "Front/Patient/my_patient_portal.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Try to find patient by email (matching the logged-in user's email)
        user = self.request.user
        patient = None
        
        if user.is_authenticated:
            try:
                # Try to find patient by email
                patient = Patient.objects.get(email=user.email)
            except Patient.DoesNotExist:
                # Patient record not found for this user
                context['patient'] = None
                context['no_patient_record'] = True
                return context
            except Patient.MultipleObjectsReturned:
                # Multiple patients with same email - get the first one
                patient = Patient.objects.filter(email=user.email).first()
        
        if not patient:
            context['patient'] = None
            context['no_patient_record'] = True
            return context
        
        context['patient'] = patient
        
        # Get all medical history entries
        history_entries = patient.medical_history_entries.select_related(
            'doctor', 'related_appointment'
        ).all()
        
        # Get all appointments
        appointments = patient.appointments.all()
        
        # Create a unified timeline
        timeline_items = []
        
        # Add medical history entries to timeline
        for entry in history_entries:
            timeline_items.append({
                'type': 'history_entry',
                'date': entry.entry_date,
                'object': entry,
                'sort_date': entry.entry_date,
            })
        
        # Add all appointments to timeline
        for appointment in appointments:
            timeline_items.append({
                'type': 'appointment',
                'date': appointment.requested_date,
                'object': appointment,
                'sort_date': appointment.requested_date,
            })
        
        # Sort timeline by date (most recent first)
        timeline_items.sort(key=lambda x: x['sort_date'], reverse=True)
        
        # Calculate billing summary
        total_amount = sum(apt.price for apt in appointments)
        unpaid_amount = sum(apt.price for apt in appointments if apt.payment_status == 'unpaid')
        paid_amount = sum(apt.price for apt in appointments if apt.payment_status == 'paid')
        unpaid_appointments = [apt for apt in appointments if apt.payment_status == 'unpaid']
        
        context['timeline_items'] = timeline_items
        context['total_entries'] = len(history_entries)
        context['total_appointments'] = len(appointments)
        context['hospitalization_count'] = history_entries.filter(is_hospitalization=True).count()
        context['no_patient_record'] = False
        
        # Billing context
        context['total_amount'] = total_amount
        context['unpaid_amount'] = unpaid_amount
        context['paid_amount'] = paid_amount
        context['unpaid_appointments'] = unpaid_appointments
        
        # Get all medical tests requested for this patient
        context['medical_tests'] = patient.medical_tests.select_related(
            'appointment', 'requested_by'
        ).all()
        
        # Get all messages for this patient
        context['messages'] = patient.messages.select_related('sender').all()
        context['unread_messages_count'] = patient.messages.filter(
            is_read=False, sender_type='doctor'
        ).count()
        context['message_form'] = MessageForm()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle patient sending a message to doctor."""
        user = request.user
        try:
            patient = Patient.objects.get(email=user.email)
        except Patient.DoesNotExist:
            messages.error(request, "Patient record not found.")
            return redirect('my_patient_portal')
        
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.patient = patient
            message.sender = request.user
            message.sender_type = 'patient'
            message.save()
            
            messages.success(request, 'Message sent successfully! Your doctor will respond soon.')
            return redirect('my_patient_portal')
        
        # If form is invalid, reload page with errors
        context = self.get_context_data()
        context['message_form'] = form
        return self.render_to_response(context)


def export_patient_pdf(request, pk):
    """
    Export a patient's complete file as PDF.
    """
    patient = get_object_or_404(Patient, pk=pk)
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="patient_{patient.last_name}_{patient.first_name}.pdf"'
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    title = Paragraph(f"Patient Medical File", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Patient name
    patient_name = Paragraph(f"<b>{patient.first_name} {patient.last_name}</b>", styles['Heading2'])
    elements.append(patient_name)
    elements.append(Spacer(1, 20))
    
    # General Information Section
    elements.append(Paragraph("General Information", heading_style))
    general_data = [
        ['Field', 'Value'],
        ['Full Name', f"{patient.first_name} {patient.last_name}"],
        ['CIN', patient.cin or 'N/A'],
        ['Date of Birth', str(patient.date_of_birth)],
        ['Phone', patient.phone],
        ['Email', patient.email],
        ['Address', patient.address],
        ['Medical History', patient.medical_history or 'N/A'],
    ]
    
    general_table = Table(general_data, colWidths=[2*inch, 4*inch])
    general_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(general_table)
    elements.append(Spacer(1, 20))
    
    # Hospitalization Information Section
    elements.append(Paragraph("Hospitalization Information", heading_style))
    hosp_data = [
        ['Field', 'Value'],
        ['Hospitalization Status', patient.get_hospitalisation_display()],
        ['Type', patient.get_type_hosp_display() or 'N/A'],
        ['Entry Date', str(patient.date_entree_hosp) if patient.date_entree_hosp else 'N/A'],
        ['Exit Date', str(patient.date_sortie_hosp) if patient.date_sortie_hosp else 'N/A'],
        ['Responsible Doctor', str(patient.medecin_responsable) if patient.medecin_responsable else 'N/A'],
        ['Medical File', patient.dossier_medical or 'N/A'],
        ['Last Update', patient.date_derniere_mise_a_jour.strftime('%Y-%m-%d %H:%M')],
    ]
    
    hosp_table = Table(hosp_data, colWidths=[2*inch, 4*inch])
    hosp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(hosp_table)
    elements.append(Spacer(1, 20))
    
    # Medical History Entries Section
    history_entries = patient.medical_history_entries.all().order_by('-entry_date')
    if history_entries:
        elements.append(Paragraph("Medical History Entries", heading_style))
        
        for entry in history_entries:
            # Entry header
            entry_header = f"<b>{entry.get_entry_type_display()}</b> - {entry.entry_date}"
            if entry.doctor:
                entry_header += f" | Dr. {entry.doctor}"
            elements.append(Paragraph(entry_header, styles['Heading3']))
            
            # Entry details
            entry_data = []
            
            if entry.is_hospitalization:
                entry_data.append(['Hospitalization', 'Yes'])
                if entry.hospitalization_start:
                    hosp_info = f"{entry.hospitalization_start}"
                    if entry.hospitalization_end:
                        duration = entry.get_duration_days()
                        hosp_info += f" to {entry.hospitalization_end} ({duration} days)"
                    entry_data.append(['Hospitalization Period', hosp_info])
                if entry.hospitalization_type:
                    entry_data.append(['Type', entry.get_hospitalization_type_display()])
            
            if entry.symptoms:
                entry_data.append(['Symptoms', entry.symptoms[:200] + '...' if len(entry.symptoms) > 200 else entry.symptoms])
            if entry.diagnosis:
                entry_data.append(['Diagnosis', entry.diagnosis[:200] + '...' if len(entry.diagnosis) > 200 else entry.diagnosis])
            if entry.treatment:
                entry_data.append(['Treatment', entry.treatment[:200] + '...' if len(entry.treatment) > 200 else entry.treatment])
            if entry.medications:
                entry_data.append(['Medications', entry.medications[:200] + '...' if len(entry.medications) > 200 else entry.medications])
            if entry.doctor_notes:
                entry_data.append(['Doctor Notes', entry.doctor_notes[:200] + '...' if len(entry.doctor_notes) > 200 else entry.doctor_notes])
            
            if entry_data:
                entry_table = Table(entry_data, colWidths=[1.5*inch, 4.5*inch])
                entry_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(entry_table)
                elements.append(Spacer(1, 12))
    
    # Appointments Section
    appointments = patient.appointments.all().order_by('-requested_date')
    if appointments:
        elements.append(Paragraph("Linked Appointments", heading_style))
        appt_data = [['Date', 'Time', 'Department', 'Doctor', 'Status']]
        
        for appointment in appointments:
            appt_data.append([
                str(appointment.requested_date),
                appointment.requested_time.strftime('%H:%M'),
                appointment.get_department_display(),
                appointment.doctor_name or 'N/A',
                appointment.get_status_display(),
            ])
        
        appt_table = Table(appt_data, colWidths=[1.2*inch, 0.8*inch, 1.5*inch, 1.5*inch, 1*inch])
        appt_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        elements.append(appt_table)
    else:
        elements.append(Paragraph("No linked appointments found.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    return response

@require_POST
def mark_payment(request, appointment_id):
    """
    Mark an appointment as paid.
    This is a simplified payment system - in production, integrate with actual payment gateway.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Get payment method from form
    payment_method = request.POST.get('payment_method', 'online')
    
    # Mark as paid
    appointment.payment_status = 'paid'
    appointment.payment_date = timezone.now()
    appointment.payment_method = payment_method
    appointment.save()
    
    messages.success(request, f'Payment of {appointment.price} TND processed successfully!')
    
    # Redirect back to patient portal
    return redirect('my_patient_portal')



class MessagesListView(ListView):
    """Doctor's view to see all patient conversations."""
    model = Message
    template_name = 'Back/Patient/messages_list.html'
    context_object_name = 'messages'
    
    def get_queryset(self):
        # Group messages by patient, show latest message from each conversation
        from django.db.models import Max, Q, Count
        
        # Get all patients who have exchanged messages
        patient_ids = Message.objects.values_list('patient_id', flat=True).distinct()
        patients_with_messages = Patient.objects.filter(id__in=patient_ids)
        
        conversations = []
        for patient in patients_with_messages:
            latest_message = patient.messages.first()  # Already ordered by -created_at
            unread_count = patient.messages.filter(is_read=False, sender_type='patient').count()
            conversations.append({
                'patient': patient,
                'latest_message': latest_message,
                'unread_count': unread_count,
            })
        
        # Sort by latest message time
        conversations.sort(key=lambda x: x['latest_message'].created_at if x['latest_message'] else timezone.now(), reverse=True)
        return conversations
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_unread'] = Message.objects.filter(is_read=False, sender_type='patient').count()
        return context


class MessageConversationView(TemplateView):
    """View conversation with a specific patient (for doctors)."""
    template_name = 'Back/Patient/message_conversation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_id = kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id)
        
        # Get all messages for this patient
        messages = Message.objects.filter(patient=patient).order_by('created_at')
        
        # Mark patient messages as read
        messages.filter(sender_type='patient', is_read=False).update(is_read=True)
        
        context['patient'] = patient
        context['messages'] = messages
        context['form'] = MessageForm()
        return context
    
    def post(self, request, *args, **kwargs):
        patient_id = kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id)
        form = MessageForm(request.POST)
        
        if form.is_valid():
            message = form.save(commit=False)
            message.patient = patient
            message.sender = request.user
            message.sender_type = 'doctor'
            message.save()
            
            messages.success(request, 'Message sent successfully!')
            return redirect('message_conversation', patient_id=patient.id)
        
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)

