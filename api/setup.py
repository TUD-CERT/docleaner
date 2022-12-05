from setuptools import setup, find_namespace_packages

setup(name="docleaner-api",
      packages=find_namespace_packages(where='src', include=['docleaner.*']),
      package_dir={'': 'src'})
