import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from PyPDF2 import PdfWriter


def _create_user(username="alice", password="pass"):
    return User.objects.create_user(username=username, password=password)


def _make_pdf(path, title="Extract Title", author="Extract Author"):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title, "/Author": author})
    with open(path, 'wb') as f:
        writer.write(f)


@pytest.mark.django_db
def test_extract_sync(tmp_path):
    user = _create_user()
    client = APIClient()
    token_resp = client.post('/api/token-auth/', {"username": "alice", "password": "pass"})
    token = token_resp.data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    pdf_path = tmp_path / 'extract.pdf'
    _make_pdf(pdf_path)
    with open(pdf_path, 'rb') as f:
        up = client.post('/api/documents/', {"file": f})
    assert up.status_code == 201
    doc_id = up.data['id']

    resp = client.post(f'/api/documents/{doc_id}/extract/')
    assert resp.status_code == 200
    assert resp.data['is_processed'] is True
    assert resp.data['title']
    assert resp.data['md5']


