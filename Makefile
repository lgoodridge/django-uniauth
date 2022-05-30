# Makefile

ENV?=

clean:
	rm -f *.pyc

# Perform initial developer setup
# You will still need to setup tox to work with multiple
# python environements, perhaps with pyenv
install:
	pip install -r requirements.txt
	pip install tox

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
