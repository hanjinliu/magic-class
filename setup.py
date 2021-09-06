from setuptools import setup, find_packages

with open("magicclass/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]
      
setup(name="magic-class",
      version=VERSION,
      description="",
      author="Hanjin Liu",
      author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
      license="GPLv2",
      packages=find_packages(),
      install_requires=[
            "matplotlib",
            "magicgui>=0.2.10",
      ],
      python_requires=">=3.7",
      )