PYFILES := `echo *.py */[^_]*.py`

all: check test

check:
  ruff check {{PYFILES}}
  ty check {{PYFILES}}
  vermin -vv --no-tips -i {{PYFILES}}
  md-link-checker

test:
  python3 -m unittest -v test_argparse_from_file

build:
  rm -rf dist
  uv build

upload: build
  uv-publish

format:
  ruff check --select I --fix {{PYFILES}} && ruff format {{PYFILES}}

clean:
  rm -vrf *.egg-info build/ dist/ __pycache__/ */__pycache__
