# CCO Membership Site Backend

This repository contains the backend code for the CCO Membership Site, a Django-based project designed to manage
various aspects of user accounts, organizations, tasks, file uploads, navigation bars, and an annual compliance review
tool. This README file provides an overview of the project's structure, functionality, and setup instructions, aimed at
helping new developers quickly understand and contribute to the project.

## Table of Contents

- [Key Points and Overview](#key-points-and-overview)
- [Project Structure](#project-structure)
- [Applications Overview](#applications-overview)
    - [Accounts](#accounts)
    - [Conf](#conf)
    - [Navbar](#navbar)
    - [File Hub](#file-hub)
    - [Organization](#organization)
    - [Task](#task)
    - [ACR Tool](#acr-tool)
    - [Utils](#utils)
- [Setup Instructions](#setup-instructions)
    - [Prerequisites](#prerequisites)
    - [Environment Variables](#environment-variables)
    - [Database Setup](#database-setup)
    - [Running the Project](#running-the-project)
- [API Endpoints](#api-endpoints)

## Key Points and Overview

- **Django-based project:** The CCO Membership Site Backend is built using Django, a powerful web framework for Python.
- **Modular architecture:** The project is organized into multiple Django apps, each responsible for a specific
  functionality.
- **Celery integration:** Task scheduling and management are handled using Celery, allowing for background processing.
- **AWS S3 for file storage:** The project uses AWS S3 for secure and scalable file storage.
- **Docker support:** The project includes Docker and Docker Compose configurations for containerized deployment.
- **RESTful API:** The project exposes a RESTful API with detailed endpoints for managing users, organizations, tasks,
  and more.

## Project Structure

The project is organized into various Django applications, each handling a specific part of the functionality. Below is
an overview of the main directories and files:

```
.
├── accounts                 # Handles user-related operations and task scheduling
├── acr_tool                 # Manages the annual compliance review process
├── conf                     # Contains project-wide settings and configurations
├── docker                   # Docker-related scripts and configuration
├── file_hub                 # Manages file uploads and storage on AWS S3
├── navbar                   # Handles navigation bar configurations
├── organization             # Manages organization-related operations
├── task                     # Handles task creation and management
├── utils                    # Utility functions, including AWS S3 interactions
├── manage.py                # Django's command-line utility
├── Dockerfile               # Docker configuration file
├── docker-compose.yaml      # Docker Compose configuration file
├── requirements.txt         # Python dependencies
└── celerybeat-schedule.db   # Celery beat schedule database
```

## Applications Overview

### Accounts

**Overview:**
The `accounts` app manages user-related operations, including user creation, login, and profile updates. It also
contains a task scheduling mechanism using Celery to inactivate user accounts after a specified active period.

**Key Features:**

- **User management (CRUD operations):** Handles creating, reading, updating, and deleting user accounts.
- **Organization management:** Automatically creates or updates an organization when a user is created or updated.
- **Task scheduling:** Inactivates user accounts after their active period expires using Celery.

**Main API Functionalities:**

- `POST /users/signup/` - Sign up a new user and create a new organization.
- `PUT /users/update/<int:pk>/` - Update an existing user's details and associated organization.
- `POST /account/login/` - Log in for admin user.
- `POST /account/cco_login/` - Log in for cco user.
- `POST /account/logout/` - Log out a user.

### Conf

**Overview:**
The `conf` app contains project-wide settings and configurations, including Django settings, Celery settings, and schema
generation for API documentation.

**Key Features:**

- **Django settings:** Manages the global configuration of the project.
- **Celery configuration:** Configures Celery for task scheduling.
- **Schema generator:** Custom schema generator for OpenAPI documentation, supporting both HTTP and HTTPS.
- **Root URL configuration:** Centralized URL configuration with Swagger API documentation.

**Main API Functionalities:**

- **Swagger documentation:** Access API documentation at `/api/docs/`.

### Navbar

**Overview:**
The `navbar` app manages the navigation bar configurations for different organizations. It allows CRUD operations on
navbar items and custom organization-specific navigation bars.

**Key Features:**

- **CRUD operations:** Manage navbar and sub-navbar items.
- **Organization-specific navigation bars:** Customize the navbar for different organizations.

**Main API Functionalities:**

- `GET /navbar/` - List all navbar items.
- `POST /navbar/` - Create a new navbar item.
- `GET /organization-navbars/<int:org_id>/` - Get and update custom navbar for an organization.

### File Hub

**Overview:**
The `file_hub` app manages file uploads to AWS S3 and stores metadata in the database. It provides APIs for uploading,
retrieving, updating, and deleting files.

**Key Features:**

- **File upload to AWS S3:** Uses Boto3 to upload files to AWS S3.
- **Metadata management:** Stores file metadata in PostgreSQL.
- **File conversion:** Converts files to Base64 format.

**Main API Functionalities:**

- `POST /file/upload/` - Upload a file to AWS S3 and save metadata.
- `GET /file/` - List all uploaded files.
- `DELETE /file/<int:pk>/delete/` - Delete a file.

### Organization

**Overview:**
The `organization` app manages organizations, including their creation, update, and deletion. It also handles the
association of users with organizations.

**Key Features:**

- **CRUD operations:** Manage organizations and related data.
- **User-organization association:** Links users to their respective organizations.

**Main API Functionalities:**

- `POST /organization/` - Create a new organization.
- `GET /organization/list/` - List all organizations.
- `PUT /organization/<int:pk>/update/` - Update an organization's details.

**Models:**

- `Organization` - Represents an organization with fields like `company_name`, `email_address`, and `contract_duration`.
- `BasicTemplate` - Represents a basic template used in the organization.

### Task

**Overview:**
The `task` app handles task creation, management, and history tracking. It allows users to create tasks, assign them to
organizations, and manage their status over time.

**Key Features:**

- **Task management:** Create, update, and delete tasks with different frequencies.
- **Task history tracking:** Track changes made to tasks over time.
- **File management:** Upload and manage files associated with tasks.

**Main API Functionalities:**

- `POST /task/create/` - Create a new task.
- `GET /task/` - List all tasks.
- `PUT /task/<int:pk>/update/` - Update a task.

**Models:**

- `Task` - Represents a task with fields like `task_title`, `schedule_date`, and `frequency`.
- `TaskHistory` - Tracks changes made to tasks.
- `OrganizationTask` - Associates tasks with organizations.
- `OrganizationUserTask` - Associates tasks with organization users.

**Celery Task:**

- `update_download_links` - Regenerates downloadable S3 file links daily to ensure they remain valid over time.

### ACR Tool

**Overview:**
The `acr_tool` app handles the annual compliance review process, including the creation and management of regulatory
reviews, risk assessments, and associated questions and responses.

**Key Features:**

- **Compliance management:** Manage SEC rule links, regulatory reviews, and risk assessments.
- **Custom permissions:** Define roles like SuperUser and CCO for specific access control.

**Main API Functionalities:**

- `POST /sec_rule_links/create/` - Create a new SEC rule link.
- `GET /regulatory_reviews/` - List all regulatory reviews.
- `POST /risk_assessment_sections/create/` - Create a new risk assessment section.

### Utils

**Overview:**
The `utils` package contains utility functions that support various operations across the project, particularly
interactions with AWS S3.

**Key Features:**

- **AWS S3 interaction:** Provides utility functions to upload files to S3, generate pre-signed URLs, and manage S3
  resources.
- **Reusable utilities:** Functions in this package can be reused across different apps within the project.

**Main Functionalities:**

- **S3 file upload:** Upload files to AWS S3 and return the file URL.
- **Generate pre-signed URLs:** Generate URLs for accessing S3 files securely.
- **Directory management:** Manage directory structures in S3 for different organizations and tasks.

## Setup Instructions

### Prerequisites

Before setting up the project, ensure you have the following installed on your system:

- Python 3.11
- PostgreSQL
- Docker (optional, for containerized setup)
- Docker Compose (optional, for containerized setup)

### Environment Variables

Create a `.env` file in the root of the project to store the necessary environment variables:

```
DEBUG=True
DATABASE_URL=postgres://username:password@localhost:5432/dbname
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
S3_BUCKET_NAME=your_s3_bucket_name
AWS_REGION=your_aws_region
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Database Setup

1. Create a PostgreSQL User and Database::

   ```bash
    --  Open a terminal and connect to PostgreSQL as a superuser:
    psql -U postgres
    CREATE DATABASE CCO_membership_site;
   
    -- Create a new PostgreSQL user
    CREATE USER CCO_memberships_user WITH PASSWORD '$r!@U$3r';
    
    -- Create a new database
    CREATE DATABASE CCO_database;
    
    -- Grant all privileges on the new database to the user
    GRANT ALL PRIVILEGES ON DATABASE CCO_database TO CCO_memberships_user;
    
    -- Connect to the new database
    \c CCO_database
    
    -- Grant necessary privileges on the schema
    GRANT USAGE ON SCHEMA public TO CCO_memberships_user;
    GRANT CREATE ON SCHEMA public TO CCO_memberships_user;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CCO_memberships_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CCO_memberships_user;
    
    -- Exit psql
    \q
   ```

2. Apply migrations to set up the database schema:

   ```bash
   python manage.py migrate
   ```

### Running the Project

1. **Without Docker:**

   Install the dependencies and start the server:

   ```bash
   pip install -r requirements.txt
   python manage.py runserver
   ```

2. **With Docker:**

   Build and start the Docker containers:

   ```bash
   docker-compose up --build
   ```

### Running Celery

Start the Celery worker and Celery Beat scheduler:

```bash
celery -A conf worker --loglevel=info
celery -A conf beat --loglevel=info
```

## API Endpoints

The project includes a wide range of API endpoints, which are documented and accessible through Swagger. After running
the project, you can access the API documentation at:

```
http://localhost:8000/api/docs/
```

## Conclusion

This project is designed to provide a comprehensive backend system for managing user accounts, organizations, tasks,
files, and compliance reviews. With a well-structured codebase and a clear separation of concerns across different
Django apps, it is easy to extend and maintain. The setup instructions provided above should help you get the project up
and running quickly. 
