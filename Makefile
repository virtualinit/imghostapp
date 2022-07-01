.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

.PHONY: env
devel:
	pip3 install -r requirements.txt

.PHONY: migrations
migrations:
	python3 manage.py makemigrations

.PHONY: migrate
migrate:
	python3 manage.py migrate

.PHONY: static
static:
	python3 manage.py collectstatic --noinput

.PHONY: run
run:
	python3 manage.py runserver 0:8080

.PHONY: test
test:
	python3 manage.py test imagehostingapp.tests
