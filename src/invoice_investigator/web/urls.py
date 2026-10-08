from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .approval_views import confirmation
from .case_views import case_detail, case_list
from .evidence_views import document, record

urlpatterns = [
    path("", case_list, name="case-list"),
    path("sign-in/", LoginView.as_view(template_name="review/login.html"), name="login"),
    path("sign-out/", LogoutView.as_view(), name="logout"),
    path("cases/<slug:case_id>/", case_detail, name="case-detail"),
    path("cases/<slug:case_id>/proposals/<uuid:proposal_id>/", confirmation, name="confirmation"),
    path(
        "cases/<slug:case_id>/revisions/<int:number>/evidence/<str:name>/",
        document,
        name="document",
    ),
    path("cases/<slug:case_id>/revisions/<int:number>/records/<str:name>/", record, name="record"),
]
