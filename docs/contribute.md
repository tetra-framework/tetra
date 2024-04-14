---
title: Contributing
---

# Contributing to the project

You can help/contribute in many ways:

* Bring in new ideas and [discussions](https://github.com/tetra-framework/tetra/discussions)
* Report bugs in our [issue tracker](https://github.com/tetra-framework/tetra/issues)
* Add documentation
* Write code


## Writing code

Fork the repository locally and install it as editable package:

```bash
git clone git@github.com:tetra-framework/tetra.git
cd tetra
python -m pip install -e .
```


### Code style

* Please only write [Black](https://github.com/psf/black) styled code. You can automate that by using your IDE's save
trigger feature.
* Document your code well, using [Napoleon style docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html#example-google).
* Write appropriate tests for your code.