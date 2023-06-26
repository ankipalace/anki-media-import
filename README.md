# Development

## Installing packages needed for development
```bash
pip install -r dev-requirements.txt
```

## Building the add-on
```bash
python scripts/build.py
```

## Type checking
You need to build the add-on first:
```bash
python scripts/build.py
```

Then you can run mypy:
```bash
mypy
```
