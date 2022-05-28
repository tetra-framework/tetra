import setuptools
from tetra import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tetraframework",
    version=__version__,
    url='https://www.tetraframework.com',
    author="Sam Willis",
    description="Full stack component framework for Django using Alpine.js",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    packages=setuptools.find_packages(exclude='demosite'),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    install_requires=[
        'cryptography>=37.0.1',
        'Django>=4.0.3',
        'python-dateutil>=2.8.2',
        'sourcetypes>=0.0.2',
    ]
)
