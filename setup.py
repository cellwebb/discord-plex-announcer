"""Setup script for plex_announcer package."""

from setuptools import find_packages, setup

setup(
    name="plex_announcer",
    version="0.2.0",
    description="Discord bot that announces new media added to a Plex server",
    author="Cell Webb",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "discord.py",
        "plexapi",
        "requests",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "plex-announcer=plex_announcer.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Multimedia :: Video",
    ],
)
