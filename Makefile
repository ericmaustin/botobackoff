.PHONY: build publish-test install-dev test

test:
	PYTHONPATH=. pytest -v

clean:
	-@rm -dr build dist

install-dev:
	@pip install -r requirements-dev.txt

build:
	@python setup.py sdist
	@python setup.py bdist_wheel

publish-test: clean build
	@twine upload --repository testpypi dist/*

publish: clean build
	@twine upload --repository pypi dist/*