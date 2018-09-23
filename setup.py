import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pandas-mssql",
    version="0.3",
    author="Connell Blackett",
    description= \
        "Pandas DataFrame methods for reading from and writing to SQL Server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/connellblackett/pandas-mssql",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)