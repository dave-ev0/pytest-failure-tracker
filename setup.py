from setuptools import setup, find_packages

setup(
    name="pytest-analytics",
    version="1.0.0",
    description="A pytest plugin that tracks test analytics, failures, and performance metrics",
    author="Dave McCrory",
    author_email="dave@ev0.ai",
    url="https://github.com/dmccror1/pytest-analytics",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pytest>=6.0.0",
        "duckdb>=0.9.0"
    ],
    entry_points={
        "pytest11": ["analytics = pytest_analytics.plugin"]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.8",
)
