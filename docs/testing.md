---
title: Testing
---

# Testing

Testing Tetra is done using pytest. Make sure you have npm (or yarn etc.) installed, Tetra needs esbuild for building 
the frontend components before testing.

```bash
python -m pip install .[dev]
cd tests
npm install
```

Within the `tests` directory, just call `pytest` to test Tetra components.

```bash
pytest
```