import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tetraframework",
    version="0.0.5",
    url="https://www.tetraframework.com",
    author="Sam Willis",
    description="Transition package to 'tetra'",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "tetra>=0.1.0",
    ],
)
