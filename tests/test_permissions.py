import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from PyPDF2 import PdfWriter


def _make_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(path, 'wb') as f:
        writer.write(f)


@pytest.mark.django_db
def test_document_isolated_between_users(tmp_path):
    alice = User.objects.create_user(username="alice", password="pass")
    bob = User.objects.create_user(username="bob", password="pass")

    alice_client = APIClient()
    t1 = alice_client.post('/api/token-auth/', {"username": "alice", "password": "pass"}).data['token']
    alice_client.credentials(HTTP_AUTHORIZATION=f'Token {t1}')

    bob_client = APIClient()
    t2 = bob_client.post('/api/token-auth/', {"username": "bob", "password": "pass"}).data['token']
    bob_client.credentials(HTTP_AUTHORIZATION=f'Token {t2}')

    pdf_path = tmp_path / 'p.pdf'
    _make_pdf(pdf_path)
    with open(pdf_path, 'rb') as f:
        up = alice_client.post('/api/documents/', {"file": f})
    doc_id = up.data['id']

    # Bob cannot see Alice's document
    resp = bob_client.get(f'/api/documents/{doc_id}/')
    assert resp.status_code == 404


