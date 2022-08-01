"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from src.awsc.version import version
from setuptools import setup, find_packages

with open("README.md", "r") as readme:
    ld = readme.read()

setup(
    name="awsc",
    url="https://github.com/baliame/awsc",
    version=version,
    description="AWS Commander",
    long_description=ld,
    long_description_content_type="text/markdown",
    author="baliame",
    author_email="akos.toth@cheppers.com",  # Optional
    classifiers=[  # Optional
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
    ],
    package_dir={"": "src"},  # Optional
    packages=find_packages(where="src"),  # Required
    python_requires=">=3.8, <4",
    install_requires=[
        "blessed>=1.17.12",
        "gnupg>=1.3.2",
        "cryptography>=3.1",
        "pyyaml>=5.3.1",
        "boto3>=1.16.33",
        "jq>=1.1.1",
        "pyperclip>=1.8.1",
        "numpy>=1.17.4",
    ],
    entry_points={  # Optional
        "console_scripts": [
            "awsc=awsc:main",
        ],
    },
)
