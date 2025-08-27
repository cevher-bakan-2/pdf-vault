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
def test_extract_async_creates_job(tmp_path):
    user = User.objects.create_user(username="alice", password="pass")
    client = APIClient()
    token = client.post('/api/token-auth/', {"username": "alice", "password": "pass"}).data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    p = tmp_path / 'a.pdf'
    _make_pdf(p)
    with open(p, 'rb') as f:
        up = client.post('/api/documents/', {"file": f})
    doc_id = up.data['id']

    r = client.post(f'/api/documents/{doc_id}/extract/?async=true')
    assert r.status_code == 202
    # jobs endpoint should list the job
    jobs = client.get('/api/jobs/')
    assert jobs.status_code == 200
    assert len(jobs.data) >= 1


