from glob import glob
from setuptools import setup, find_namespace_packages


setup(name="docleaner-api",
      entry_points={
            "console_scripts": ["docleaner-ctl=docleaner.api.entrypoints.ctl.main:main"]
      },
      data_files=[
            ("api/entrypoints/web/templates", glob("src/docleaner/api/entrypoints/web/templates/*.html")),
            ("api/entrypoints/web/templates/doc", glob("src/docleaner/api/entrypoints/web/templates/doc/*.html")),
            ("api/entrypoints/web/templates/theme", glob("src/docleaner/api/entrypoints/web/templates/theme/*.html")),
            ("api/entrypoints/web/templates/errors", glob("src/docleaner/api/entrypoints/web/templates/errors/*")),
            ("api/entrypoints/web/static/dist", glob("src/docleaner/api/entrypoints/web/static/dist/*")),
      ],
      include_package_data=True,
      install_requires=[
            "fastapi",
            "jinja2",
            "motor",
            "podman",
            "python-magic",
            "python-multipart",
            "uvicorn[standard]",
            # Workaround for incompatible urllib3/requests update
            "requests<2.29.0",
            "urllib3<2.0.0"
      ],
      packages=find_namespace_packages(where="src", include=["docleaner.*"]),
      package_dir={"": "src"},
      url="https://docleaner.cert.tu-dresden.de",
      author="TUD-CERT",
      author_email="cert@tu-dresden.de",
      version="20230608")
