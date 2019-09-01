"""
Package that contains the ranking algorithms used by the EVote software (@2008-2019)
"""
import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('evote_ranking/__init__.py', 'r') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read()).group(1)))

setup(
    name='evote_ranking',
    version=version,
    url='https://github.com/mdipierro/evote_ranking',
    license='BSD',
    author='Massimo Di Pierro',
    author_email='massimo.dipierro@gmail.com',
    maintainer='Massimo Di Pierro',
    maintainer_email='massimo.dipierro@gmail.com',
    description='The EVote Ranking algorithms',
    long_description=__doc__,
    packages=[],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
