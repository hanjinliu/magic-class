from setuptools import setup, find_packages

with open("magicclass/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]
      
setup(name="magic-class",
      version=VERSION,
      description="Generate multifunctional GUIs from classes",
      author="Hanjin Liu",
      author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
      license="GPLv2",
      download_url="https://github.com/hanjinliu/magic-class",
      packages=find_packages(),
      install_requires=[
            "magicgui>=0.2.11",
            "numpy>=1.20.3",
            "matplotlib>=3.4.2"
      ],
      python_requires=">=3.7",
      )