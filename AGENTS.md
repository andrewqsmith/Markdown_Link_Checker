# mdlinkcheck

Python 3 (>= 3.9), standard library only. Tests use pytest; fixtures live in
`tests/fixtures/` and must stay offline.

## Build / install for development

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

## Test

```sh
python -m pytest -q
```

## Run

```sh
python -m mdlinkcheck <folder>
```

Exit codes: `0` no broken links, `1` broken links found, `2` bad arguments
(missing/not-a-directory path, or invalid usage).
