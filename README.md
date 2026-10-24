# FoodSaver AI 🍃

### AI-Powered Food Waste Management Platform for Surplus Identification and Redistribution Optimization

FoodSaver AI is a web-based food waste management platform designed to help businesses manage food inventory, monitor expiry dates, identify potential food waste, and make surplus food visible to NGOs and community kitchens for redistribution.

**Project Status:** Milestone 1 — Inventory Management and Expiry Tracking  
**Development Status:** In Progress

## Overview

Food waste can occur when restaurants, grocery stores, and supermarkets fail to monitor inventory and approaching expiry dates effectively. At the same time, NGOs and community kitchens may struggle to identify available surplus food.

FoodSaver AI aims to bridge this gap through a centralized platform that combines inventory management, expiry monitoring, waste-risk assessment, and surplus food visibility.

## Objectives

- Simplify food inventory management for businesses.
- Monitor food expiry dates and classify expiry urgency.
- Identify food items that may require attention using rule-based risk assessment.
- Help NGOs and community kitchens discover eligible surplus food.
- Establish a foundation for future AI-based waste prediction and redistribution optimization.

## Implemented Features — Milestone 1

- **User authentication:** Registration and login for application users.
- **Role-based access:** Separate workflows for business/food-provider users and NGO/community-kitchen users.
- **Inventory management:** Add, view, update, and delete food inventory records.
- **Expiry tracking:** Classify food items according to their remaining shelf life.
- **Waste-risk assessment:** Use rule-based logic to estimate food waste risk.
- **Inventory search and filtering:** Find records using available search and filter controls.
- **CSV import:** Upload food inventory data in bulk through a CSV interface.
- **Business dashboard:** Display inventory records and available summary information.
- **NGO dashboard:** Display eligible, unexpired surplus food from providers.
- **Administrative management:** Use Django's administrative interface for authorized management tasks.

*Feature descriptions should be retained only where the corresponding functionality is implemented and verified in the published code.*

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Django |
| Frontend | HTML, CSS, Bootstrap 5, Django Templates |
| Database | SQLite for local development |
| Data processing | Python |
| Bulk data import | CSV |
| Version control | Git and GitHub |

**Note:** PostgreSQL/Supabase integration and advanced AI forecasting are not presented as completed features unless they have been implemented and tested.

## How the Application Works

1. A user registers and signs in to the platform.
2. A business user manages food inventory records and expiry information.
3. The application classifies expiry urgency and calculates risk using predefined rules.
4. Users search and filter inventory records or import data through the CSV interface.
5. NGOs and community kitchens can view eligible surplus food for potential redistribution.

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version supported by the project's dependencies.
- pip
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Dasari-Saniya/FoodSaver-AI.git
cd FoodSaver-AI
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks environment activation, use Command Prompt:

```bat
venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Apply database migrations

```bash
python manage.py migrate
```

### 5. Create an administrator account (optional)

```bash
python manage.py createsuperuser
```

Follow the prompts to configure your own administrator credentials.

### 6. Start the development server

```bash
python manage.py runserver
```

Open the following address in your browser:

http://127.0.0.1:8000/

Keep the terminal running while using the application.

## Demo Data

If the project includes the `populate_demo_data` management command, you can use it to generate demonstration inventory records:

```bash
python manage.py populate_demo_data
```

If you want demo records associated with a specific existing business account, use the supported username option:

```bash
python manage.py populate_demo_data --username YOUR_BUSINESS_USERNAME
```

Replace `YOUR_BUSINESS_USERNAME` with the username of an existing account. Review the command's implementation before running it to confirm its behavior.

## Running Tests

Run Django's system checks:

```bash
python manage.py check
```

Run the inventory application's tests:

```bash
python manage.py test inventory
```

Use the actual terminal results when reporting test status. Do not claim that all tests pass unless the commands complete successfully.

## Project Documentation

The repository can include the following supporting material:

- `docs/` — Project reports and milestone documentation.
- `docs/screenshots/` — Selected screenshots of the implemented application.
- `docs/FoodSaver_AI_Milestone_1_Screenshot_Documentation.pdf` — Milestone 1 screenshot report, if included.

Screenshots and reports document the visible progress of the project; the source code remains the primary reference for implementation details.

## Planned Enhancements

The following are potential future improvements and are not claimed as completed in Milestone 1:

- Machine-learning-based food waste and demand forecasting.
- Integration of forecasting models such as Prophet or LSTM, subject to data availability and validation.
- Automated notifications for approaching expiry dates.
- Improved surplus food pickup coordination.
- Food donation impact analytics and sustainability reporting.
- Gamification features to encourage food waste reduction.
- Deployment with a production-ready database and hosting configuration.

## Project Status

Milestone 1 focuses on the core inventory-management workflow, expiry tracking, basic waste-risk assessment, CSV import, and surplus visibility.

Development is ongoing, with future milestones intended to expand prediction, coordination, and impact-reporting capabilities.

## Author

**Saniya Dasari**  
B.Tech — Computer Science and Engineering, 2027 Batch

- GitHub: https://github.com/Dasari-Saniya
- LinkedIn: https://www.linkedin.com/in/dasari-saniya/

## Disclaimer

This project is under active development. Features, setup requirements, and supported workflows may change as additional milestones are implemented and validated.
