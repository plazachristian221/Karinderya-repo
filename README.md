LuckyPaw – Pet Essentials Store

**1. Business Name and Description**

Business Name: PawMart

PawMart is a pet supplies e-commerce system where customers can browse pet products, create accounts, log in, and manage their orders. Administrators can manage products and review system records.

**2. Problem Being Solved**

Small pet supply businesses may need a simple way to display their products and manage product records and customer orders. PawMart provides a centralized website for browsing products and managing store information.

**3. Features**

Landing Page: Introduces the business and displays store information.

User Accounts: Registration, login, logout, and password hashing.

Role-Based Access: Separates administrator and regular-user access.

Product CRUD: Create, view, update, and delete products.

Input Validation: Checks required fields and invalid product values.

Delete Confirmation: Helps prevent accidental product deletion.

Order Management: Allows customers to place and view orders.

Nearby Branch Suggestions: Displays sample branch locations on a map.

Persistent Database: Stores application records in PostgreSQL.

Update this list to match the features that actually work in your submitted code.

4. Technology Stack

Python

VS Code

Flask

HTML and CSS

Bootstrap

JavaScript

PostgreSQL

Railway for deployment

Git and GitHub for version control

**5. Setup and Run Instructions**

Prerequisites

Python 3 installed

Git installed

A PostgreSQL database, if using PostgreSQL

Installation

Clone the repository:

git clone YOUR_GITHUB_REPOSITORY_URL

Open the project folder:

cd petstore

Create a virtual environment:

python -m venv .venv

Activate it on Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Configure the required environment variables, including DATABASE_URL and SECRET_KEY. Use your own local or hosted PostgreSQL database connection string. Do not commit secrets to GitHub.

Run the application using the command appropriate for your project:

python app.py

Open the local URL shown in the terminal, usually http://127.0.0.1:5000.

Deployment

The application can be deployed to Railway by connecting the GitHub repository, configuring the required environment variables and PostgreSQL database, and setting the appropriate start command.

**6. AI Tools Used**

ChatGPT was used to assist with code development, debugging, HTML templates, database integration, input validation, CRUD functionality, and deployment troubleshooting. The code was reviewed and tested during development.

**7. Test Accounts**

Administrator

Email or username: REPLACE_WITH_ADMIN_LOGIN

Password: REPLACE_WITH_ADMIN_TEST_PASSWORD

Regular User

Email: REPLACE_WITH_TEST_USER_EMAIL

Password: REPLACE_WITH_TEST_USER_PASSWORD

Use working test accounts created specifically for evaluation. Confirm that the administrator can manage products and that a regular user cannot access administrator-only functions. Do not publish personal passwords, production credentials, or database secrets.
