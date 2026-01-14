# 

 is a secure, internal file storage and sharing platform built with Django. It allows users to upload, organize, preview, stream, and share files while maintaining strict permission control. The system is designed to run on a single physical drive using logical isolation rather than disk partitioning.

 is intended for teams and organizations that need predictable behavior, clear access rules, and full control over how files are stored and served.

---

## What  Does

* Stores documents and media securely in one place
* Ensures users only see files they own or are allowed to access
* Supports previews and streaming directly in the browser
* Tracks all activity for auditing and administration
* Avoids unnecessary abstraction or third-party storage services

---

## Key Features

### File Management

* Upload files up to 10GB (configurable)
* Automatic file type detection (documents, images, audio, video, archives)
* Virtual folders for logical organization
* In-browser preview for images, PDFs, audio, and video
* Multi-file uploads

### User Management

* User registration and login
* Secure authentication using Django’s built-in system
* Personal dashboard showing storage usage and activity
* Admin dashboard for system-wide visibility

### Security and Permissions

* Fine-grained permissions: Read, Write, Admin
* File sharing with explicit access control
* Centralized audit logging of all file actions
* Filename sanitization and path traversal protection
* CSRF protection enabled by default

### Media Streaming

* Byte-range streaming for large audio and video files
* Fast seeking and immediate playback
* Streaming sessions tracked per user
* Direct downloads with correct MIME handling

### Administration

* System-wide activity monitoring
* Storage usage statistics per user
* Access and audit logs with filtering
* Monitoring of active streams and failed access attempts

---

## Technology Stack

* **Backend:** Django 4.2, Python 3.12
* **Database:** SQLite (development), PostgreSQL (production-ready)
* **Frontend:** HTML5, CSS3, Vanilla JavaScript
* **Storage:** Custom local storage using UUID-based filenames
* **Media Handling:** Manual byte-range streaming and MIME detection

---

## Installation

### Prerequisites

* Python 3.8 or higher
* pip

### Setup Steps

Clone the repository:

```bash
git clone <repository-url>
cd storageApp
```

Create and activate a virtual environment:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure settings:

```bash
cp storageApp/settings.example.py storageApp/settings.py
```

Edit `settings.py`:

* Set `DEBUG = False` for production
* Configure the database
* Set `ALLOWED_HOSTS`
* Adjust file storage paths if needed

Initialize the database:

```bash
python manage.py makemigrations
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

Collect static files:

```bash
python manage.py collectstatic
```

Run the development server:

```bash
python manage.py runserver
```

Access the application at: `http://localhost:8000`

---

## Project Structure

```
storageApp/
├── app/              # Core application logic
│   ├── models.py
│   ├── views.py
│   ├── services.py
│   ├── static/
│   └── templates/
├── storage/          # Physical file storage (UUID blobs)
├── storageApp/       # Project configuration
├── manage.py
└── requirements.txt
```

---

## Configuration

### Environment Variables

For production environments:

```bash
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DATABASE_URL=postgres://user:password@localhost/dbname
```

### File Storage

* Default path: `storage/blobs/`
* Maximum upload size: 10GB (configurable)
* Supports common document and media formats

### Security Settings

Important production settings:

* `CSRF_COOKIE_SECURE = True`
* `SESSION_COOKIE_HTTPONLY = True`
* `ALLOWED_HOSTS` properly configured

---

## Using 

### For Users

**Uploading Files**

* Click "Upload"
* Select or drag files
* Files are automatically categorized and ready for preview

**Managing Files**

* View and filter files
* Preview directly in the browser
* Download when needed

**Sharing Files**

* Select a file you own
* Assign access permissions to another user
* Shared files appear automatically for the recipient

### For Administrators

* View system-wide usage and activity
* Monitor active streaming sessions
* Review audit logs
* Analyze storage usage per user

---

## Security Notes

* Files are never served directly by the web server
* All access goes through permission checks
* Files are stored with UUID-based names
* Direct path access is blocked

---

## Testing

Run all tests:

```bash
python manage.py test app.tests
```

Run specific test groups:

```bash
python manage.py test app.tests.ModelTests
python manage.py test app.tests.ViewTests
python manage.py test app.tests.ServiceTests
```

---

## Deployment Overview

* Use Nginx or Apache as a reverse proxy
* Run Django with Gunicorn or uWSGI
* Enable HTTPS
* Use PostgreSQL for production
* Configure backups for files and database

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure tests pass
5. Open a pull request

Follow PEP 8 standards and keep commits clear and focused.

---

## License

MIT License. See the LICENSE file for details.

---

## Support

If you need help:

* Review the documentation
* Search existing issues
* Open a new issue with clear steps and details

---
