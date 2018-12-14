
from setuptools import setup

setup(name='rqd',
      version='0.1',
      packages=['rqd'],
      entry_points={
          'console_scripts': [
              'rqd=rqd.rqd:main'
          ]
      })

