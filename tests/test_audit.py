import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from PyPDF2 import PdfWriter
from documents.models import AuditLog


def _make_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(path, 'wb') as f:
        writer.write(f)


@pytest.mark.django_db
def test_audit_upload_extract_delete(tmp_path):
    user = User.objects.create_user(username="alice", password="pass")
    client = APIClient()
    token = client.post('/api/token-auth/', {"username": "alice", "password": "pass"}).data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    p = tmp_path / 'a.pdf'
    _make_pdf(p)
    with open(p, 'rb') as f:
        up = client.post('/api/documents/', {"file": f})
    doc_id = up.data['id']

    client.post(f'/api/documents/{doc_id}/extract/')
    client.delete(f'/api/documents/{doc_id}/')

    actions = list(AuditLog.objects.filter(owner=user).values_list('action', flat=True))
    assert 'UPLOAD' in actions
    assert 'EXTRACT' in actions
    assert 'DELETE' in actions


