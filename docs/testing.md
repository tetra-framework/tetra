---
title: Testing
---

# Testing

Testing Tetra is done using pytest. Make sure you have npm (or yarn etc.) installed, Tetra needs `esbuild` and `chromium webdriver` for building the frontend components before testing.

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