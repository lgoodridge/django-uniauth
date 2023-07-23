import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="django-uniauth",
    version="1.4.1",
    author="Lance Goodridge",
    author_email="ldgoodridge95@gmail.com",
    keywords=["django", "auth", "authentication", "cas", "sso", "single sign-on"],
    description="A Django app for managing CAS and custom user authentication.",
    include_package_data=True,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lgoodridge/django-uniauth",
    license='LGPLv3',
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    install_requires=[
        "Django>=1.11",
        "python-cas>=1.4.0",
        "djangorestframework-simplejwt>=4.1.0",
    ],
    extras_require = {
        ":python_version<='3.2'": ["mock"],
    },
    packages=setuptools.find_packages(exclude=["demo-app",]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2",
        "Framework :: Django :: 3",
        "Framework :: Django :: 4",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ]
)
