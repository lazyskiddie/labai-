from django.db import models


class TrainingData(models.Model):
    source      = models.CharField(max_length=50, default="admin")
    filename    = models.CharField(max_length=200, blank=True)
    val_count   = models.IntegerField(default=0)
    values_json = models.TextField(default="{}")
    features    = models.TextField(default="[]")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "training_data"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.val_count} values)"


class UserUpload(models.Model):
    filename    = models.CharField(max_length=200, blank=True)
    val_count   = models.IntegerField(default=0)
    flagged_cnt = models.IntegerField(default=0)
    ml_score    = models.IntegerField(null=True, blank=True)
    values_json = models.TextField(default="{}")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_uploads"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.val_count} values)"


class ModelWeights(models.Model):
    model_id      = models.CharField(max_length=20, primary_key=True, default="current")
    weights_json  = models.TextField(default="[]")
    stats_json    = models.TextField(default="{}")
    version       = models.IntegerField(default=1)
    training_size = models.IntegerField(default=0)
    trained_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "model_weights"

    def __str__(self):
        return f"Model v{self.version} ({self.training_size} records)"


class BatchJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("done",    "Done"),
        ("error",   "Error"),
    ]
    total     = models.IntegerField(default=0)
    processed = models.IntegerField(default=0)
    saved     = models.IntegerField(default=0)
    skipped   = models.IntegerField(default=0)
    failed    = models.IntegerField(default=0)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "batch_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job #{self.id} {self.status} ({self.processed}/{self.total})"


class BatchItem(models.Model):
    STATUS_CHOICES = [
        ("waiting",    "Waiting"),
        ("processing", "Processing"),
        ("ready",      "Ready"),
        ("saved",      "Saved"),
        ("skipped",    "Skipped"),
        ("failed",     "Failed"),
    ]
    job         = models.ForeignKey(BatchJob, on_delete=models.CASCADE, related_name="items")
    filename    = models.CharField(max_length=200)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")
    val_count   = models.IntegerField(default=0)
    values_json = models.TextField(default="{}")
    error       = models.TextField(blank=True)

    class Meta:
        db_table = "batch_items"

    def __str__(self):
        return f"{self.filename} [{self.status}]"