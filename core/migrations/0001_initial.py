from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TrainingData",
            fields=[
                ("id",          models.BigAutoField(primary_key=True)),
                ("source",      models.CharField(max_length=50, default="admin")),
                ("filename",    models.CharField(max_length=200, blank=True)),
                ("val_count",   models.IntegerField(default=0)),
                ("values_json", models.TextField(default="{}")),
                ("features",    models.TextField(default="[]")),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "training_data", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UserUpload",
            fields=[
                ("id",          models.BigAutoField(primary_key=True)),
                ("filename",    models.CharField(max_length=200, blank=True)),
                ("val_count",   models.IntegerField(default=0)),
                ("flagged_cnt", models.IntegerField(default=0)),
                ("ml_score",    models.IntegerField(null=True, blank=True)),
                ("values_json", models.TextField(default="{}")),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "user_uploads", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ModelWeights",
            fields=[
                ("model_id",      models.CharField(max_length=20, primary_key=True, default="current")),
                ("weights_json",  models.TextField(default="[]")),
                ("stats_json",    models.TextField(default="{}")),
                ("version",       models.IntegerField(default=1)),
                ("training_size", models.IntegerField(default=0)),
                ("trained_at",    models.DateTimeField(null=True, blank=True)),
            ],
            options={"db_table": "model_weights"},
        ),
        migrations.CreateModel(
            name="BatchJob",
            fields=[
                ("id",         models.BigAutoField(primary_key=True)),
                ("total",      models.IntegerField(default=0)),
                ("processed",  models.IntegerField(default=0)),
                ("saved",      models.IntegerField(default=0)),
                ("skipped",    models.IntegerField(default=0)),
                ("failed",     models.IntegerField(default=0)),
                ("status",     models.CharField(max_length=20, default="pending")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "batch_jobs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BatchItem",
            fields=[
                ("id",          models.BigAutoField(primary_key=True)),
                ("job",         models.ForeignKey("core.BatchJob", on_delete=django.db.models.deletion.CASCADE, related_name="items")),
                ("filename",    models.CharField(max_length=200)),
                ("status",      models.CharField(max_length=20, default="waiting")),
                ("val_count",   models.IntegerField(default=0)),
                ("values_json", models.TextField(default="{}")),
                ("error",       models.TextField(blank=True, default="")),
            ],
            options={"db_table": "batch_items"},
        ),
    ]