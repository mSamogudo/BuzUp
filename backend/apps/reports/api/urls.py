from django.urls import path

from apps.reports.api.views import (
    DashboardChartsView,
    DashboardView,
    ExportTransactionsView,
    ExportValidationsView,
    OperationalRevenueReportView,
    ReconciliationView,
    ReportBuilderListView,
    ReportBuilderRunView,
    RevenueReportView,
    ValidationReportView,
)

urlpatterns = [
    path("admin/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("admin/dashboard/charts/", DashboardChartsView.as_view(), name="dashboard-charts"),
    path("admin/reports/revenue/", RevenueReportView.as_view(), name="report-revenue"),
    path("admin/reports/operational-revenue/", OperationalRevenueReportView.as_view(), name="report-operational-revenue"),
    path("admin/reports/validations/", ValidationReportView.as_view(), name="report-validations"),
    path("admin/reconciliation/payments/", ReconciliationView.as_view(), name="reconciliation-payments"),
    path("admin/exports/validations/", ExportValidationsView.as_view(), name="export-validations"),
    path("admin/exports/transactions/", ExportTransactionsView.as_view(), name="export-transactions"),
    # Unified report builder
    path("admin/reports/builder/", ReportBuilderListView.as_view(), name="report-builder-list"),
    path("admin/reports/builder/<str:kind>/", ReportBuilderRunView.as_view(), name="report-builder-run"),
]
