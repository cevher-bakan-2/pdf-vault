# pdfvault

PDF'den Veri Çıkarıcı & Arşivleyici – Django + DRF demo projesi.

## Kurulum

1) Sanal ortam ve bağımlılıklar (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install "Django>=5,<6" djangorestframework django-filter PyPDF2 pdfplumber python-magic-bin drf-spectacular celery redis pytest pytest-django model_bakery pillow
```

2) Geliştirme sunucusu ve migrasyonlar:

```powershell
python manage.py migrate
python manage.py runserver
```

3) Token almak için kullanıcı oluştur:

```powershell
python manage.py createsuperuser
```

Ardından şu endpoint'ten token al:

```bash
curl -X POST http://localhost:8000/api/token-auth/ -d "username=<USER>&password=<PASS>"
```

## API Özet

- /api/folders/ (CRUD)
- /api/tags/ (CRUD)
- /api/documents/
  - POST: dosya yükleme ("file")
  - GET: listeleme + filtre/arama (q, tag, folder, processed, created_after/before, ordering)
  - GET /api/documents/{id}/: detay
  - PATCH: title/author/folder/tags güncelle
  - DELETE: sil
  - POST /api/documents/{id}/extract/?async=true|false
  - GET /api/documents/{id}/download/
- /api/jobs/ (list/retrieve)
- /api/audit-logs/ (list)
- /api/schema/ ve /api/docs/ (Swagger UI)

Varsayılan auth: `TokenAuthentication`. Tüm endpointler `IsAuthenticated` ve obje bazında owner kontrolü uygular.

## Testler

```powershell
pytest -q
```

## Notlar

- Yalnızca PDF kabul edilir (uzantı + imza). Maks boyut: 20MB.
- pdfplumber + PyPDF2 ile metadata ve metin çıkarılır; md5 hesaplanır.
- Opsiyonel Celery/Redis entegrasyonu için `CELERY_BROKER_URL=redis://localhost:6379/0` belirtip `documents/tasks.py` ekleyebilirsiniz.