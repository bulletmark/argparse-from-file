NAME = $(shell basename $(CURDIR))
PYNAME =  $(subst -,_,$(NAME))
PYFILES = $(wildcard $(PYNAME)/[^_]*.py)

check:
	ruff check $(PYFILES)
	mypy $(PYFILES)
	pyright $(PYFILES)
	vermin -vv --no-tips -i $(PYFILES)
	md-link-checker

build::
	rm -rf dist
	uv build

upload: build
	uv-publish

format::
	ruff check --select I --fix $(PYFILES) && ruff format $(PYFILES)

clean::
	@rm -vrf *.egg-info build/ dist/ __pycache__/ */__pycache__
