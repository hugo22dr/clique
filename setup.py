from setuptools import setup, Extension
import sys

module = Extension('click_sync',
                  sources=['click_sync.c'],
                  extra_compile_args=['-O3', '-march=native'],
                  libraries=['pthread', 'rt'],
                  include_dirs=['/usr/include/python{}.{}'.format(sys.version_info.major, sys.version_info.minor)])

setup(name='click_sync',
      version='1.0',
      ext_modules=[module],
      package_dir={'': '.'})