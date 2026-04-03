from django.urls import path
from . import views

urlpatterns = [
    # ── Pages ──────────────────────────────────────────────────────
    path("",       views.index_view,  name="index"),
    path("user",   views.user_view,   name="user"),
    path("admin",  views.admin_view,  name="admin_page"),
    path("health", views.health_view, name="health"),

    # ── Auth ───────────────────────────────────────────────────────
    path("api/auth/login", views.api_login, name="api_login"),

    # ── User API ───────────────────────────────────────────────────
    path("api/ocr",           views.api_ocr,           name="api_ocr"),
    path("api/user/save",     views.api_user_save,     name="api_user_save"),
    path("api/model/current", views.api_model_current, name="api_model_current"),

    # ── Admin: Batch ───────────────────────────────────────────────
    path("api/admin/batch/start",
         views.api_batch_start, name="api_batch_start"),
    path("api/admin/batch/<int:job_id>/status",
         views.api_batch_status, name="api_batch_status"),
    path("api/admin/batch/<int:job_id>/item/<path:filename>/approve",
         views.api_batch_approve, name="api_batch_approve"),
    path("api/admin/batch/<int:job_id>/item/<path:filename>/skip",
         views.api_batch_skip, name="api_batch_skip"),

    # ── Admin: Data ────────────────────────────────────────────────
    path("api/admin/stats",                    views.api_admin_stats,    name="api_admin_stats"),
    path("api/admin/training",                 views.api_admin_training, name="api_admin_training"),
    path("api/admin/training/<int:rid>",       views.api_delete_training,name="api_delete_training"),
    path("api/admin/uploads",                  views.api_admin_uploads,  name="api_admin_uploads"),
    path("api/admin/uploads/clear",            views.api_clear_uploads,  name="api_clear_uploads"),

    # ── Admin: Model ───────────────────────────────────────────────
    path("api/admin/model/train",  views.api_train_model,  name="api_train_model"),
    path("api/admin/model/deploy", views.api_deploy_model, name="api_deploy_model"),
]