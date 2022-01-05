from distutils.core import setup, Extension

winps = Extension('winps',
                    define_macros = [('MAJOR_VERSION', '1'),
                                     ('MINOR_VERSION', '0')],
                    include_dirs = [],
                    libraries = [],
                    library_dirs = [],
                    sources = ['winps.cpp'])

setup (name = 'winps',
       version = '1.0',
       description = 'Windows ps for RQD',
       ext_modules = [winps])
