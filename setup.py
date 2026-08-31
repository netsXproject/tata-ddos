
from setuptools import setup, find_packages

setup(
    name="tata-ddos",
    version="1.1.0",
    description="Enterprise-grade stress testing with proxy support",
    author="nezX",
    author_email="nezx@protonmail.com",
    url="https://github.com/nezX-project/tata-ddos",
    packages=find_packages(),
    install_requires=[
        'rich>=13.0.0',
        'aiohttp>=3.8.0',
        'pysocks>=1.7.1',
        'requests>=2.28.0',
        'beautifulsoup4>=4.11.0',
        'reportlab>=4.0.0',
    ],
    entry_points={
        'console_scripts': [
            'tata=tata:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Security Professionals',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Rust',
    ],
)
