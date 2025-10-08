# Automated_Review_Sheet_Generator

Project Review - Deployment Guide

Prerequisites
- Docker 24+ installed
- A reachable MySQL server (8.x recommended)

Environment variables
- SECRET_KEY: Flask secret key
- DB_HOST, DB_USER, DB_PASSWORD, DB_NAME: MySQL connection details

First-time build (on any system)
```bash
docker build -t project-review:latest .
```

Run locally
```bash
docker run --rm -p 8000:8000 \
  -e SECRET_KEY='change-me' \
  -e DB_HOST='your-mysql-host' \
  -e DB_USER='your-user' \
  -e DB_PASSWORD='your-pass' \
  -e DB_NAME='project_review1' \
  -v $(pwd)/generated_pdfs:/app/generated_pdfs \
  -v $(pwd)/stored_files:/app/stored_files \
  project-review:latest
```

Access the app: http://localhost:8000

Database setup (once)
1) Ensure the target MySQL has an empty schema named DB_NAME (default: project_review1)
2) Import SQL
```bash
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < databaseFinal.sql
```

Transfer image to a new system
Option A – Save/Load tar
```bash
# On source system
docker save project-review:latest -o project-review.tar

# Move project-review.tar to the new system (scp/rsync/usb)

# On new system
docker load -i project-review.tar
```

Option B – Push/Pull from a registry
```bash
# Tag & push (after docker login)
docker tag project-review:latest yourrepo/project-review:latest
docker push yourrepo/project-review:latest

# On new system
docker pull yourrepo/project-review:latest
```

Run on a new system
```bash
docker run --rm -p 8000:8000 \
  -e SECRET_KEY='change-me' \
  -e DB_HOST='your-mysql-host' \
  -e DB_USER='your-user' \
  -e DB_PASSWORD='your-pass' \
  -e DB_NAME='project_review1' \
  -v $(pwd)/generated_pdfs:/app/generated_pdfs \
  -v $(pwd)/stored_files:/app/stored_files \
  project-review:latest
```

Notes
- The container serves via Gunicorn on port 8000.
- WeasyPrint/Cairo system packages are preinstalled for PDF generation.
- Map volumes if you need persistence of PDFs/data.