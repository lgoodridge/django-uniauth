# Makefile

ENV?=

clean:
	rm -f *.pyc

# Formats the code with black and isort
format:
	python3.10 -m isort uniauth/
	python3.10 -m black uniauth/
	python3.10 -m isort tests/
	python3.10 -m black tests/

# Perform initial developer setup
# You will still need to setup tox to work with multiple
# python environements, perhaps with pyenv
install:
	pip install -r requirements.txt
	pip install tox

# Install formatting tools in python3.10 environment
# Requires having python3.10 setup, perhaps with pyenv
install-formatter:
	pip3.10 install black
	pip3.10 install isort

# Create migrations
# Requires having the demo_app set up
migrations:
	cd demo_app; python manage.py makemigrations

# Run all tests
test:
	tox

# Test a specific environment
# e.g. make test-env ENV=py39-django40
test-env:
	tox -e ${ENV}

# Run after a dependency / supported verion update
# to recreate test environments
test-recreate:
	tox -r

# Upload a new build to pypi
upload_pypi: clean
	python setup.py sdist bdist_wheel
	twine upload dist/* --skip-existing
