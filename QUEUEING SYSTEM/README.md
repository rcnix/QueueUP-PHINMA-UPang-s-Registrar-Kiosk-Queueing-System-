**🎟️ QueueUP: PHINMA-UPang's Registrar Kiosk-Queueing System**

A smarter queue starts before the number is called.

QueueUP is an open-source, PostgreSQL-backed queue management system designed for the PHINMA-University of Pangasinan Registrar.

Instead of treating queueing as simply “take a number and wait,” QueueUP connects the entire process — from the moment a recipient creates a ticket, to the moment a registrar serves it, to the moment the transaction becomes part of the institution's records.

It brings together self-service ticketing, counter management, administration, transaction monitoring, receipt printing, and public queue displays into one system.

// REQUIREMENTS

Before running QueueUP, make sure you have:

    - Python 3.10 or newer
    - PostgreSQL
    - A PostgreSQL database for QueueUP
    - A Windows environment if you want to use the receipt-printing functionality

        NOTE: Windows is recommended for printing because pywin32 is included in the project's Windows requirements.


// INSTALLATION

    -- Clone the repository and open a terminal in the repository root — the directory containing requirements.txt.

    -- Create a virtual environment:

    -- py -m venv .venv

// ACTIVATION:

    -- .\.venv\Scripts\Activate.ps1

// LIBRARIES:

-- python -m pip install -r requirements.txt

// DATABASE CONFIGURATION //

CREATE:
    QUEUEING SYSTEM/.env

Then add your PostgreSQL connection information:

    DB_NAME=queueup
    DB_USER=postgres
    DB_PASSWORD=your-password
    DB_HOST=localhost
    DB_PORT=5432

DB_PORT is optional and defaults to 5432.

Create the PostgreSQL database before launching QueueUP.

**KEEP YOUR CREDENTIALS PRIVATE!**

Do not commit .env to the repository.

Your database password belongs on your machine — not in source control.

A typical .gitignore should contain:

.env
.venv/
__pycache__/

## First Launch

From the `QUEUEING SYSTEM` directory, run:

    py main.py

The first launch prompts you to create the admin name and password. Later launches use the Admin, Counter User, or Kiosk User buttons on the login screen. Create counter-user accounts in **Counter Creation**; each counter user signs in to the interface for their assigned counter. Create shared kiosk credentials in the **Kiosk User** section, listed below Counter Creation in the admin menu. The kiosk can also run as a standalone public window:

    py main.py kiosk

## Counter Password Map

Counter passwords remain hashed for sign-in and are also stored reversibly so an admin can view newly created counter credentials in **Counter Creation** after re-entering the admin password. Anyone with direct database access can read those saved passwords. Passwords for counter accounts created before this feature was added cannot be recovered.

Kiosk login credentials are managed in the **Kiosk User** section and their password is stored as a one-way hash.

## Resetting the App Schema

This permanently deletes every table and record in the configured database's `public` schema. Back up the database first. Connect to the database named by `DB_NAME` in `.env` as its owner or a PostgreSQL superuser, then run:

    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public AUTHORIZATION your_db_user;

Replace `your_db_user` with the value of `DB_USER` in `.env`. Then run `py main.py`; QueueUP recreates its tables on startup and prompts you to create a new admin.