import os
import setuptools

from distutils.util import convert_path

version_ns = {}
version_path = convert_path('pywim/_version.py')
with open(version_path) as version_file:
    exec(version_file.read(), version_ns)

version = version_ns['__version__']

build_num = os.getenv('BUILD_NUMBER')

if build_num:
    version += '.' + str(build_num)

setuptools.setup(
    name='teton-pywim',
    version=version,
    author='Teton Simulation',
    author_email='info@tetonsim.com',
    packages=setuptools.find_packages(exclude=['test']),
    install_requires=['requests', 'scipy', 'teton-3mf']
)
