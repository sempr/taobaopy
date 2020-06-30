all: coverage

coverage-html:
	pytest --cov=taobaopy --cov-report html .

coverage:
	pytest --cov=taobaopy .
