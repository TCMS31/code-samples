from django.urls import path

from analysis.views import AnalysisView

urlpatterns = [
    path("", AnalysisView.as_view(), name="analysis"),
]
