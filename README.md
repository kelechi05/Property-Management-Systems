# Property Management System

A comprehensive Django-based property management application designed for landlords and property managers.

## Project Structure

```
property_management/
├── manage.py                 # Django management script
├── config/                   # Main project configuration
│   ├── settings/
│   │   ├── base.py          # Base settings
│   │   ├── dev.py           # Development settings
│   │   └── prod.py          # Production settings
│   ├── urls.py              # Main URL configuration
│   ├── asgi.py              # ASGI configuration
│   └── wsgi.py              # WSGI configuration
├── apps/                    # Core business applications
│   ├── accounts/            # User account management
│   ├── properties/          # Property management
│   ├── tenants/             # Tenant management
│   ├── leases/              # Lease management
│   ├── payments/            # Payment processing
│   ├── maintenance/         # Maintenance requests
│   └── reports/             # Reports and analytics
├── website/                 # Public-facing website
│   ├── templates/website/   # Website templates
│   └── static/website/      # Website static files
├── dashboard/               # Authenticated user dashboard
│   ├── templates/dashboard/ # Dashboard templates
│   └── static/dashboard/    # Dashboard static files
├── core/                    # Shared utilities and services
├── templates/               # Shared templates
├── static/                  # Global static files
├── media/                   # User-uploaded media
├── requirements/            # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

## Features

- **Property Management**: Add, update, and manage multiple properties
- **Tenant Management**: Track tenant information and agreements
- **Lease Management**: Create and manage lease agreements
- **Payment Processing**: Record and track rent payments
- **Maintenance Tracking**: Log and manage maintenance requests
- **Reporting**: Generate financial and operational reports
- **User Authentication**: Secure user account management
- **Public Website**: Showcase properties and services
- **Dashboard**: Authenticated area for property owners and managers

## Prerequisites

- Python 3.8+
- pip or conda
- Virtual environment (recommended)

## Installation

1. **Clone or extract the project**
   ```bash
   cd property_management
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files** (production)
   ```bash
   python manage.py collectstatic
   ```

## Usage

### Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

### Admin Panel

Access the Django admin panel at `http://localhost:8000/admin/`

### Dashboard

After logging in, access the dashboard at `http://localhost:8000/dashboard/`

## Environment Variables

Key variables to configure in `.env`:

- `DEBUG`: Set to `False` in production
- `SECRET_KEY`: Generated Django secret key
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Database connection string
- `EMAIL_HOST`: SMTP server for sending emails
- `EMAIL_HOST_USER`: Email account for sending emails
- `EMAIL_HOST_PASSWORD`: Email account password

## Database Models

### Key Models

- **Property**: Represents a rental property
- **Tenant**: User account for tenants
- **Lease**: Agreement between owner and tenant
- **Payment**: Rent payment records
- **MaintenanceRequest**: Service requests
- **Report**: Generated reports

## API Endpoints

(To be documented based on implementation)

## Contributing

Guidelines for contributing to this project:

1. Create a new branch for each feature
2. Follow PEP 8 style guide
3. Write tests for new features
4. Submit pull requests for review

## Security Considerations

- Keep `SECRET_KEY` secure
- Use HTTPS in production
- Set `DEBUG = False` in production
- Use environment variables for sensitive data
- Regularly update dependencies
- Implement proper authentication and permissions

## Testing

```bash
python manage.py test
```

## Deployment

### Using Gunicorn and Nginx

See deployment documentation for detailed instructions.

### Using Docker

(Docker configuration to be added)

## Troubleshooting

### Common Issues

**Issue**: ModuleNotFoundError: No module named 'django'
- **Solution**: Ensure virtual environment is activated and dependencies are installed

**Issue**: Database migration errors
- **Solution**: Run `python manage.py migrate` after creating new models

**Issue**: Static files not loading
- **Solution**: Run `python manage.py collectstatic`

## License

[Your License Here]

## Support

For support, contact: support@propertymanagement.com

## Changelog

### Version 1.0.0
- Initial project setup
- Core app structure
- Website and dashboard framework

