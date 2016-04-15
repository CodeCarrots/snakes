"""snakes setup script
"""

from setuptools import setup
from os import path

base_path = path.abspath(path.dirname(__file__))

with open(path.join(base_path, 'README.md')) as f:
    long_description = f.read()

setup(
    name='snakes',

    version='0.0.13-dev',

    description='Corewars-like snakes game server code',
    long_description=long_description,

    url='http://git.plocharz.info/summary/snakes.git',

    author='Krzysztof Płocharz',
    author_email='krzysztof@plocharz.info',

    license='???',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],

    packages=['snakes'],
    package_dir={'': 'src'},

    install_requires=['redis>=2.10.5'],

    entry_points={
        'console_scripts': [
            'snakes-server=snakes.judge:main',
            'snakes-manage=snakes.manage:main',
        ],
    }
)
