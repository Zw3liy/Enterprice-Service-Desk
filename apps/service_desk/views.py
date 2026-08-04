from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    DetailView,
)

from .models import Ticket
from .forms.ticket_forms import TicketCreateForm


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "tickets/ticket_list.html"  # Updated line per ChatGPT instruction
    context_object_name = "tickets"
    ordering = ["-created_at"]


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketCreateForm
    template_name = "tickets/create.html"
    success_url = reverse_lazy("service_desk:ticket_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "tickets/detail.html"
    context_object_name = "ticket"