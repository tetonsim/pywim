import setuptools

with open('requirements.txt', 'r') as freq:
    requirements = freq.readlines()

setuptools.setup(
    name="pywim",
    version="19.0.0",
    author="Teton Simulation",
    author_email="info@tetonsim.com",
    packages=setuptools.find_packages(),
    install_requires=requirements
)