from setuptools import setup, Extension
import os

# Obtém o caminho absoluto do diretório atual
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define o caminho para o arquivo fonte
source_file = os.path.join(current_dir, 'modules', 'click_sync_wrapper.c')

module = Extension(
    'click_sync',
    sources=[source_file],
    extra_compile_args=['-O3', '-march=native'],
    libraries=['pthread', 'rt']
)

setup(
    name='click_sync',
    version='1.0',
    ext_modules=[module],
    packages=['src'],
    package_dir={'': '.'}
)