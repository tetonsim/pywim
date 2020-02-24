import os
import setuptools

from pywim import __version__

version = __version__

build_num = os.getenv('BUILD_NUMBER')

if build_num:
    version += '.' + str(build_num)

setuptools.setup(
    name='teton-pywim',
    version=version,
    author='Teton Simulation',
    author_email='info@tetonsim.com',
    packages=setuptools.find_packages(exclude=['test']),
    install_requires=['requests', 'scipy', 'vtk', 'teton-3mf']
)
