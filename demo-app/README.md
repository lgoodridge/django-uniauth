## Demo App - Quick Start Guide

This app provides an example of how to setup a project to use UniAuth. It has no functionality, and exists solely to show off the installable `uniauth` app.

### Installation

From the repository root:

    # Create a virtual env
    mkvirtualenv myenv --python=$(which python3)

    # Install the dependencies
    pip install django
    pip install python-cas
    pip install django-uniauth

    # Move into the demo-app
    cd demo-app

    # Apply database migrations
    python manage.py migrate

    # (Recommended) create a superuser
    python manage.py createsuperuser

    # Run the development server
    python manage.py runserver

### Viewing the app

After running `runserver` open `http://localhost:8000/` in a browser.
