from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator


def document_upload_to(instance: "Document", filename: str) -> str:
    owner_part = f"user_{instance.owner_id}" if instance.owner_id else "anonymous"
    return f"documents/{owner_part}/{filename}"


class Folder(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return f"{self.name} (#{self.pk})"


class Tag(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="uniq_owner_tag_name"),
        ]
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class Document(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=document_upload_to,
                            validators=[FileExtensionValidator(allowed_extensions=["pdf"])])
    original_filename = models.CharField(max_length=255)
    content_text = models.TextField(blank=True)
    title = models.CharField(max_length=255, blank=True)
    author = models.CharField(max_length=255, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    md5 = models.CharField(max_length=64, blank=True)
    folder = models.ForeignKey('Folder', on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_processed = models.BooleanField(default=False)

    tags = models.ManyToManyField('Tag', related_name='documents', blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "created_at"], name="idx_doc_owner_created"),
        ]
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return self.original_filename


class ExtractionJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='jobs')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return f"Job #{self.pk} for Document #{self.document_id} [{self.status}]"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        UPLOAD = "UPLOAD", "Upload"
        EXTRACT = "EXTRACT", "Extract"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        DOWNLOAD = "DOWNLOAD", "Download"

    class TargetType(models.TextChoices):
        DOCUMENT = "DOCUMENT", "Document"
        FOLDER = "FOLDER", "Folder"
        TAG = "TAG", "Tag"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=Action.choices)
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_id = models.CharField(max_length=64)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return f"{self.owner_id} {self.action} {self.target_type} {self.target_id}"


# Create your models here.
