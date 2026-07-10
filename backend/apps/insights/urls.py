from django.urls import path

from .views import AnomalyDetectionView, DemandForecastView, ReorderSuggestionsView

urlpatterns = [
    path("insights/reorder-suggestions/", ReorderSuggestionsView.as_view(), name="reorder-suggestions"),
    path("insights/demand-forecast/", DemandForecastView.as_view(), name="demand-forecast"),
    path("insights/anomalies/", AnomalyDetectionView.as_view(), name="anomalies"),
]
