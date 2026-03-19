# Shipping Management System

Enterprise-grade shipping operations management platform for Cocoa Marketing Company (Ghana) Ltd. - Tema Port Operations.

## Overview

The Shipping Management System is a comprehensive Django-based web application designed to streamline and digitize shipping department operations at Tema Port. The system manages the complete lifecycle of cocoa shipment operations, from booking and documentation to container evacuation and tally approval.

## Features

### Core Modules

- **SD Records Management** - Track shipping documents with multi-contract support, tonnage allocation, and balance monitoring
- **Tally System** - Digital tally creation with supervisor approval workflow and operations desk oversight
- **Booking Management** - Handle vessel bookings with contract-specific tracking and documentation
- **Declaration Tracking** - Manage customs declarations with contract-level granularity and document uploads
- **Evacuation Monitoring** - Track container movements from terminals to port with real-time status updates
- **Schedule Management** - Create and manage departmental schedules with terminal assignments
- **Terminal Operations** - Manage 5 warehouse terminals (CWC, Commodity, Dzata Bu, Other Produce, Armajaro Global Annex)
- **Daily Port Operations** - Calendar-based daily port file management with Excel/PDF uploads

### User Roles & Permissions

- **Manager/Deputy** - Full system access, schedule creation, terminal assignment
- **Supervisors** - Terminal-specific tally approval authority
- **Operations Desk** - View and process all approved tallies
- **Declarations Desk** - Manage declaration records and documentation
- **Evacuation Team** - Log and track container evacuations
- **General Staff** - Create tallies and view schedules

## Technology Stack

- **Backend**: Django 5.1+ (Python 3.13)
- **Database**: PostgreSQL 16+
- **Deployment**: Railway.app
- **Storage**: Railway Volumes for media files
- **Web Server**: Gunicorn with WhiteNoise for static files

## Production Deployment

### Live Environment

- **URL**: https://eshipping-production.up.railway.app
- **Platform**: Railway.app
- **Database**: Managed PostgreSQL
- **Region**: US West

### Environment Variables

Required environment variables for production:

```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=<django-secret-key>
DEBUG=False
ALLOWED_HOSTS=eshipping-production.up.railway.app,*.railway.app
CSRF_TRUSTED_ORIGINS=https://eshipping-production.up.railway.app,https://*.railway.app
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Local Development Setup

### Prerequisites

- Python 3.13 or higher
- PostgreSQL 16 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Dblay112/eshipping.git
cd eshipping
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Create a `.env` file in the project root:
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/eshipping
ALLOWED_HOSTS=localhost,127.0.0.1
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Run development server:
```bash
python manage.py runserver
```

Access the application at `http://localhost:8000`

## Project Structure

```
eshipping/
├── apps/
│   ├── accounts/          # User authentication and staff profiles
│   ├── sd_tracker/        # SD records and container lists
│   ├── tally/             # Tally management and approvals
│   ├── ebooking/          # Booking management
│   ├── declaration/       # Declaration tracking
│   ├── evacuation/        # Container evacuation logs
│   └── schedule/          # Schedule and terminal management
├── eshipping/             # Project settings and configuration
├── static/                # Static assets (CSS, JS, images)
├── media/                 # User-uploaded files
├── requirements.txt       # Python dependencies
└── manage.py             # Django management script
```

## Security

- All passwords are hashed using Django's PBKDF2 algorithm
- CSRF protection enabled on all forms
- Secure session cookies in production
- HTTPS enforced via SSL redirect
- Role-based access control (RBAC) for all modules
- SQL injection protection via Django ORM

## Database Schema

The system uses PostgreSQL with the following key models:
- Account (custom user model with staff profiles)
- SDRecord (shipping documents with historical tracking)
- SDAllocation (contract-level tonnage tracking)
- TallyInfo (tally records with approval workflow)
- Booking (vessel bookings with contract details)
- Declaration (customs declarations)
- Evacuation (container movement tracking)
- Schedule (departmental schedules)
- TerminalSchedule (terminal supervisor assignments)

## Support & Maintenance

For technical support or bug reports, contact the IT department at Cocoa Marketing Company (Ghana) Ltd.

**System Administrator**: IT Department
**Business Owner**: Shipping Department - Tema Operations

## License

Proprietary software. All rights reserved.
© 2026 Cocoa Marketing Company (Ghana) Ltd.

Unauthorized copying, distribution, or modification of this software is strictly prohibited.

## Version History

- **v1.0.0** (March 2026) - Initial production release
  - Complete digitization of shipping operations
  - Multi-terminal support with supervisor workflows
  - Contract-level tracking across all modules
  - Role-based permission system
