# _*_ coding: utf-8 _*_

from os import path
from setuptools import find_packages, setup
from codecs import open

#name = 'meteva_base'
#author ="liucouhua,daikan,wangbaoli,tangbuxing"
#version =__import__(name).__version__
here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(  
    name = 'meteva_base',  
    version = '0.1.5',
    description = 'base classes and functions of generally meteorogical usage, like Basic_class/IO/calculation/plot .etc',  
    long_description=long_description,
    long_description_content_type = None,
    # author
    author = 'NMC_WFT',  
    author_email = 'pangzide003@163.com',
    # license
    license = 'MIT', 
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'Programming Language :: Python :: 3',
    ],
    #packages = ['meteva_base'],
    packages=find_packages(exclude=['docs', 'tests', 'build', 'dist']),
    include_package_data=True,
    exclude_package_data={'': ['.gitignore']},

    url = 'https://github.com/nmcdev/nimm',
    install_requires=[
                      'numpy>=1.12.1',
                      'pandas>=1.0.4',
                      "netCDF4>=1.4.2",
                      'scipy>=0.19.0',
                      'xarray>=0.10.0',
                      'scikit-learn>=0.21.2',
                      'matplotlib>=3.0.0',
                      "httplib2>=0.12.0",
                      "protobuf<3.20.0",
                      "pyshp>=2.1.0",
                      "tables>=3.4.4",
                      "urllib3>=1.21.1",
                      "eccodes>=1.5.0",
                      "eccodes-python>=0.9.9",
                      "cfgrib>=0.9.9",
                      
                      ]
)

# development mode (DOS command):
#     python setup.py develop
#     python setup.py develop --uninstall

# build mode：
#     python setup.py build --build-base=D:/test/python/build

# distribution mode:
#     python setup.py sdist             # create source tar.gz file in /dist
#     python setup.py bdist_wheel       # create wheel binary in /dist
