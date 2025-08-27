from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Folder, Tag, Document, ExtractionJob, AuditLog
from .serializers import (
    FolderSerializer,
    TagSerializer,
    DocumentUploadSerializer,
    DocumentDetailSerializer,
    DocumentUpdateSerializer,
    ExtractionJobSerializer,
    AuditLogSerializer,
)
from .permissions import IsOwner
from .filters import DocumentFilter
from .services.pdf_extractor import extract_metadata_and_text


class OwnerQuerySetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        return instance


class FolderViewSet(OwnerQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Folder.objects.all()


class TagViewSet(OwnerQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Tag.objects.all()


class DocumentViewSet(OwnerQuerySetMixin, viewsets.ModelViewSet):
    queryset = Document.objects.select_related("folder").prefetch_related("tags").all()
    permission_classes = [IsAuthenticated, IsOwner]
    filterset_class = DocumentFilter
    search_fields = ["title", "original_filename", "content_text"]
    ordering_fields = ["created_at", "title", "page_count"]

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentUploadSerializer
        if self.action in ["retrieve", "list"]:
            return DocumentDetailSerializer
        if self.action in ["partial_update", "update"]:
            return DocumentUpdateSerializer
        return DocumentDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        AuditLog.objects.create(
            owner=request.user,
            action=AuditLog.Action.UPLOAD,
            target_type=AuditLog.TargetType.DOCUMENT,
            target_id=str(document.id),
            meta={"filename": document.original_filename},
        )
        out = DocumentDetailSerializer(document, context={"request": request})
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        document = serializer.save()
        AuditLog.objects.create(
            owner=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_type=AuditLog.TargetType.DOCUMENT,
            target_id=str(document.id),
            meta={},
        )

    def perform_destroy(self, instance):
        AuditLog.objects.create(
            owner=self.request.user,
            action=AuditLog.Action.DELETE,
            target_type=AuditLog.TargetType.DOCUMENT,
            target_id=str(instance.id),
            meta={},
        )
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        document = self.get_object()
        async_flag = request.query_params.get("async") == "true"
        if async_flag:
            # Create a queued job and return immediately (optional Celery integration can hook here)
            job = ExtractionJob.objects.create(document=document, status=ExtractionJob.Status.QUEUED)
            AuditLog.objects.create(
                owner=request.user,
                action=AuditLog.Action.EXTRACT,
                target_type=AuditLog.TargetType.DOCUMENT,
                target_id=str(document.id),
                meta={"async": True, "job_id": job.id},
            )
            return Response(ExtractionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

        # Synchronous processing
        job = ExtractionJob.objects.create(document=document, status=ExtractionJob.Status.RUNNING, started_at=timezone.now())
        try:
            data = extract_metadata_and_text(document.file.path)
            for field, value in data.items():
                setattr(document, field, value)
            document.is_processed = True
            document.save(update_fields=["title", "author", "page_count", "content_text", "md5", "is_processed", "updated_at"])
            job.status = ExtractionJob.Status.SUCCESS
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])
            AuditLog.objects.create(
                owner=request.user,
                action=AuditLog.Action.EXTRACT,
                target_type=AuditLog.TargetType.DOCUMENT,
                target_id=str(document.id),
                meta={"async": False, "job_id": job.id},
            )
            return Response(DocumentDetailSerializer(document, context={"request": request}).data)
        except Exception as exc:
            job.status = ExtractionJob.Status.FAILED
            job.error_message = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error_message", "finished_at"])
            return Response({"detail": "Extraction failed", "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.file:
            raise Http404
        AuditLog.objects.create(
            owner=request.user,
            action=AuditLog.Action.DOWNLOAD,
            target_type=AuditLog.TargetType.DOCUMENT,
            target_id=str(document.id),
            meta={"filename": document.original_filename},
        )
        response = FileResponse(open(document.file.path, 'rb'), as_attachment=True, filename=document.original_filename)
        return response


class ExtractionJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExtractionJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExtractionJob.objects.filter(document__owner=self.request.user).order_by("-created_at", "id")


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AuditLog.objects.filter(owner=self.request.user).order_by("-created_at", "id")


# Create your views here.
