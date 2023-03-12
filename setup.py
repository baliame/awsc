"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as readme:
    ld = readme.read()

setup(
    name="awsc",
    url="https://github.com/baliame/awsc",
    version="0.4.0rc11",
    description="AWS Commander",
    long_description=ld,
    long_description_content_type="text/markdown",
    author="baliame",
    author_email="akos.toth@cheppers.com",  # Optional
    classifiers=[  # Optional
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    package_dir={"": "src"},  # Optional
    packages=find_packages(where="src"),  # Required
    python_requires=">=3.8, <4",
    install_requires=[
        "blessed==1.17.12",
        "cryptography>=39.0.2",
        "python-magic==0.4.27",
        "chardet==5.0.0",
        "pyyaml==5.3.1",
        "boto3==1.17.59",
        "jq==1.4.0",
        "pyperclip==1.8.1",
        "pygments>=2.14.0",
        "numpy",
        "packaging",
        "watchdog",
    ],
    entry_points={  # Optional
        "console_scripts": [
            "awsc=awsc:main",
            "awsc-creds=awsc:cred_helper",
        ],
    },
)
