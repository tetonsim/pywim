import os
import setuptools

version = '19.1.23'

#with open('requirements.txt', 'r') as freq:
#    requirements = freq.readlines()

build_num = os.getenv('BUILD_NUMBER')

if build_num:
    version += '.' + str(build_num)

setuptools.setup(
    name='teton-pywim',
    version=version,
    author='Teton Simulation',
    author_email='info@tetonsim.com',
    packages=setuptools.find_packages(),
    install_requires=['requests', 'scipy', 'vtk', 'teton-3mf']
)
