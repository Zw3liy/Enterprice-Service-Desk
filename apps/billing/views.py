from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import Invoice, Plan, Subscription, UsageRecord
from apps.billing.serializers import (
    InvoiceSerializer,
    PlanSerializer,
    SubscribeSerializer,
    SubscriptionSerializer,
    UsageRecordSerializer,
)
from apps.billing.services import BillingService
from apps.billing.usage import snapshot_usage
from apps.service_desk.tenancy import get_active_company, require_company


@login_required
def billing_dashboard(request):
    company = get_active_company(request)
    BillingService.seed_plans()
    plans = Plan.objects.filter(is_active=True)
    subscription = None
    limits = {"allowed": True, "warnings": [], "usage": {}}
    invoices = []
    if company:
        subscription = getattr(company, "subscription", None)
        limits = BillingService.check_limits(company)
        invoices = company.invoices.all()[:20]
    return render(
        request,
        "billing/dashboard.html",
        {
            "title": "Billing",
            "plans": plans,
            "subscription": subscription,
            "limits": limits,
            "invoices": invoices,
            "company": company,
        },
    )


@login_required
@require_POST
def subscribe(request):
    company = require_company(request)
    plan_code = request.POST.get("plan_code") or "starter"
    seats = int(request.POST.get("seats") or 1)
    BillingService.subscribe(
        company,
        plan_code,
        seats=seats,
        billing_email=request.POST.get("billing_email") or "",
        actor=request.user,
    )
    messages.success(request, f"Subscribed to {plan_code}.")
    return redirect("billing:dashboard")


@login_required
@require_POST
def cancel_subscription(request):
    company = require_company(request)
    BillingService.cancel(company, at_period_end=True, actor=request.user)
    messages.info(request, "Subscription will cancel at period end.")
    return redirect("billing:dashboard")


@login_required
@require_POST
def generate_invoice(request):
    company = require_company(request)
    invoice = BillingService.generate_invoice(company, actor=request.user)
    messages.success(request, f"Invoice {invoice.number} generated.")
    return redirect("billing:dashboard")


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PlanSerializer
    queryset = Plan.objects.filter(is_active=True)
    lookup_field = "code"


class SubscriptionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = get_active_company(request)
        if not company or not hasattr(company, "subscription"):
            return Response({"detail": "No subscription"}, status=404)
        return Response(SubscriptionSerializer(company.subscription).data)

    def post(self, request):
        ser = SubscribeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        company = require_company(request)
        sub = BillingService.subscribe(
            company,
            ser.validated_data["plan_code"],
            seats=ser.validated_data.get("seats") or 1,
            trial_days=ser.validated_data.get("trial_days") or 14,
            billing_email=ser.validated_data.get("billing_email") or "",
            actor=request.user,
        )
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        company = require_company(request)
        sub = BillingService.cancel(company, actor=request.user)
        return Response(SubscriptionSerializer(sub).data)


class UsageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = require_company(request)
        usage = snapshot_usage(company)
        limits = BillingService.check_limits(company)
        return Response({"usage": usage, "limits": limits})


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        company = get_active_company(self.request)
        qs = Invoice.objects.select_related("company", "subscription")
        if company:
            qs = qs.filter(company=company)
        return qs

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        BillingService.mark_paid(invoice, actor=request.user)
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        company = require_company(request)
        invoice = BillingService.generate_invoice(company, actor=request.user)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)