from setuptools import setup, find_namespace_packages

setup(name="docleaner-api",
      entry_points={
            "console_scripts": ["docleaner-ctl=docleaner.api.entrypoints.ctl.main:main"]
      },
      packages=find_namespace_packages(where="src", include=["docleaner.*"]),
      package_dir={"": "src"})
