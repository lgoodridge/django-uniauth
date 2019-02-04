import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="django-uniauth",
    version="0.2.1",
    author="Lance Goodridge",
    author_email="ldgoodridge95@gmail.com",
    keywords=["django", "auth", "authentication", "cas", "sso", "single sign-on"],
    description="A Django app for managing CAS and custom user authentication.",
    include_package_data=True,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lgoodridge/UniAuth",
    license='MIT',
    python_requires=">=3.5",
    install_requires=[
        "Django>=2.0",
        "python-cas>=1.4.0",
    ],
    packages=setuptools.find_packages(exclude=["demo-app",]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 2.1",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ]
)
