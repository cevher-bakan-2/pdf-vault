import io
import os

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from PyPDF2 import PdfWriter


@pytest.mark.django_db
def test_unauthenticated_access_401():
    client = APIClient()
    resp = client.get('/api/documents/')
    assert resp.status_code == 401


def _create_user(username="alice", password="pass"):
    user = User.objects.create_user(username=username, password=password)
    return user


def _make_pdf(path, title="Sample Title", author="Sample Author"):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title, "/Author": author})
    with open(path, 'wb') as f:
        writer.write(f)


@pytest.mark.django_db
def test_upload_valid_pdf(tmp_path):
    pdf_path = tmp_path / 'sample.pdf'
    _make_pdf(pdf_path)

    user = _create_user()
    client = APIClient()
    token_resp = client.post('/api/token-auth/', {"username": "alice", "password": "pass"})
    assert token_resp.status_code == 200
    token = token_resp.data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    with open(pdf_path, 'rb') as f:
        resp = client.post('/api/documents/', {"file": f})
    assert resp.status_code == 201, resp.data
    assert resp.data["is_processed"] is False


@pytest.mark.django_db
def test_upload_invalid_mime_rejected(tmp_path):
    user = _create_user("bob")
    client = APIClient()
    token_resp = client.post('/api/token-auth/', {"username": "bob", "password": "pass"})
    token = token_resp.data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    fake_txt = tmp_path / 'notpdf.pdf'
    fake_txt.write_text("hello")

    with open(fake_txt, 'rb') as f:
        resp = client.post('/api/documents/', {"file": f})
    assert resp.status_code in (400, 415)


