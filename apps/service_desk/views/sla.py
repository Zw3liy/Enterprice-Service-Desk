from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from apps.service_desk.forms import SLAPolicyForm
from apps.service_desk.models import SLAPolicy
from apps.service_desk.selectors.sla_selector import SLASelector


class SLAPolicyListView(LoginRequiredMixin, ListView):
    model = SLAPolicy
    template_name = "service_desk/sla/policy_list.html"
    context_object_name = "sla_policies"

    def get_queryset(self):
        return SLAPolicy.objects.all().order_by("name")


class SLAPolicyCreateView(LoginRequiredMixin, CreateView):
    model = SLAPolicy
    form_class = SLAPolicyForm
    template_name = "service_desk/sla/policy_form.html"
    success_url = reverse_lazy("service_desk:sla:policy_list")


class SLABreachListView(LoginRequiredMixin, ListView):
    template_name = "service_desk/sla/breaches.html"
    context_object_name = "breached_tickets"

    def get_queryset(self):
        return SLASelector.get_tickets_breached_sla(self.request.user)
