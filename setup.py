from setuptools import setup, Extension
import sys

module = Extension('click_sync',
                  sources=['click_sync_wrapper.c'],
                  extra_compile_args=['-O3', '-march=native'],
                  libraries=['pthread', 'rt'])

setup(name='click_sync',
      version='1.0',
      ext_modules=[module],
      package_dir={'': '.'})