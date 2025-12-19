PYFILES := `echo */[^_]*.py`

check:
  ruff check {{PYFILES}}
  ty check --python /usr/bin/python3 {{PYFILES}}
  vermin -vv --no-tips -i {{PYFILES}}
  md-link-checker

build:
  rm -rf dist
  uv build

upload: build
  uv-publish

format:
  ruff check --select I --fix {{PYFILES}} && ruff format {{PYFILES}}

clean:
  rm -vrf *.egg-info build/ dist/ __pycache__/ */__pycache__
