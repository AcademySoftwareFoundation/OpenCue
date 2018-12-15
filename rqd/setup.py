
from setuptools import setup

setup(name='rqd',
      version='0.1',
      packages=['rqd', 'rqd.compiled_proto'],
      entry_points={
          'console_scripts': [
              'rqd=rqd.__main__:main'
          ]
      })

