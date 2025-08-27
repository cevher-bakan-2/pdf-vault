import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from PyPDF2 import PdfWriter


def _make_pdf(path, title="Invoice 123", author="ACME"):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title, "/Author": author})
    with open(path, 'wb') as f:
        writer.write(f)


@pytest.mark.django_db
def test_search_and_filters(tmp_path):
    user = User.objects.create_user(username="alice", password="pass")
    client = APIClient()
    token = client.post('/api/token-auth/', {"username": "alice", "password": "pass"}).data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    p1 = tmp_path / 'inv1.pdf'
    p2 = tmp_path / 'report.pdf'
    _make_pdf(p1, title="Invoice one", author="Alice")
    _make_pdf(p2, title="Report", author="Alice")

    with open(p1, 'rb') as f:
        d1 = client.post('/api/documents/', {"file": f}).data
    with open(p2, 'rb') as f:
        d2 = client.post('/api/documents/', {"file": f}).data

    # extract to populate metadata and text
    client.post(f"/api/documents/{d1['id']}/extract/")
    client.post(f"/api/documents/{d2['id']}/extract/")

    # search by q term in title
    r = client.get('/api/documents/?q=Invoice')
    assert r.status_code == 200
    assert len(r.data) >= 1


