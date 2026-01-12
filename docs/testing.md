---
title: Testing
---

# Testing

Testing Tetra is done using pytest. Tetra uses its bundled `esbuild` for building frontend components during tests.

```bash
make setup
```

And for e.g. Debian/Ubuntu Linux,
```bash
sudo apt install chromium-chromedriver
# start the chromedriver:
chromium.chromedriver
```

In Tetra's root dir, use the Makefile.

```bash
make test
```