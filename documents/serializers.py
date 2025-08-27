from typing import Any

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Folder, Tag, Document, ExtractionJob, AuditLog


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file", "folder", "tags"]
        read_only_fields = ["id"]

    def validate_file(self, value):
        filename = getattr(value, 'name', '')
        if not filename.lower().endswith('.pdf'):
            raise serializers.ValidationError(_("Only PDF files are allowed (by extension)."))
        size = getattr(value, 'size', 0)
        if size and size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(_("File too large. Max 20MB."))
        # Quick signature check: PDF files start with %PDF
        try:
            pos = value.tell()
        except Exception:
            pos = None
        try:
            value.seek(0)
            header = value.read(5)
        finally:
            try:
                if pos is not None:
                    value.seek(pos)
            except Exception:
                pass
        if not isinstance(header, (bytes, bytearray)) or not header.startswith(b'%PDF'):
            raise serializers.ValidationError(_("Invalid PDF file signature."))
        # MIME validation (best effort)
        try:
            import magic  # type: ignore

            mime = magic.from_buffer(value.read(2048), mime=True)
            value.seek(0)
            if mime != 'application/pdf':
                raise serializers.ValidationError(_("Invalid MIME type: %(mime)s") % {"mime": mime})
        except Exception:
            # On Windows or when libmagic not available, skip strict MIME check
            value.seek(0)
        return value

    def create(self, validated_data):
        request = self.context["request"]
        document: Document = Document(
            owner=request.user,
            original_filename=validated_data["file"].name,
            file=validated_data["file"],
            folder=validated_data.get("folder"),
        )
        document.save()
        if tags := validated_data.get("tags"):
            document.tags.set(tags)
        return document


class TagNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class FolderNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ["id", "name"]


class DocumentDetailSerializer(serializers.ModelSerializer):
    tags = TagNestedSerializer(many=True, read_only=True)
    folder = FolderNestedSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "title",
            "author",
            "page_count",
            "md5",
            "is_processed",
            "created_at",
            "updated_at",
            "folder",
            "tags",
            "file_url",
        ]
        read_only_fields = fields

    def get_file_url(self, obj: Document) -> str | None:
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(obj.file.url) if obj.file else None


class DocumentUpdateSerializer(serializers.ModelSerializer):
    # Allow updating title, author, folder, tags
    class Meta:
        model = Document
        fields = ["title", "author", "folder", "tags"]


class ExtractionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionJob
        fields = ["id", "document", "status", "error_message", "started_at", "finished_at", "created_at"]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "action", "target_type", "target_id", "meta", "created_at"]
        read_only_fields = fields


