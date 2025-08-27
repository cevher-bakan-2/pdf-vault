from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FolderViewSet, TagViewSet, DocumentViewSet, ExtractionJobViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'jobs', ExtractionJobViewSet, basename='job')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]


