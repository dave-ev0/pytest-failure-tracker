from setuptools import find_packages, setup

setup(
    name="pytest-failure-tracker",
    version="0.2.3",
    author="Krystian Safjan",
    author_email="ksafjan@gmail.com",
    description="A pytest plugin for tracking test failures over multiple runs",
    long_description=open("README.md").read(), # noqa SIM115
    long_description_content_type="text/markdown",
    url="https://github.com/izikeros/pytest-failure-tracker",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=["pytest>=6.0.0"],
    classifiers=[
        "Framework :: Pytest",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "pytest11": ["failure_tracker = pytest_failure_tracker.plugin"],
    },
    python_requires=">=3.7",
)
