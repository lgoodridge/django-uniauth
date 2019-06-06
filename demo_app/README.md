## Demo App - Quick Start Guide

This app provides an example of how to setup a project to use Uniauth. It has no functionality, and exists solely to show off the installable `uniauth` app.

### Installation

    # (Recommended) Create a virtual env
    mkvirtualenv myenv --python=$(which python3)
    
    # Install the dependencies
    pip install django
    pip install python-cas
    pip install django-uniauth
    
    # Clone the repo and move into the demo_app
    git clone https://github.com/lgoodridge/django-uniauth.git
    cd django-uniauth/demo_app

    # Apply database migrations
    python manage.py migrate
    
    # Add your CAS server(s)
    python manage.py add_institution <name> <server_url>

    # (Recommended) Create a superuser
    python manage.py createsuperuser

    # Run the development server
    python manage.py runserver

### Viewing the app

After running `runserver` open `http://localhost:8000/` in a browser.
