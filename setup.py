from setuptools import setup, find_packages

with open("magicclass/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]
      
with open("README.md", "r") as f:
    readme = f.read()
    
setup(
    name="magic-class",
    version=VERSION,
    description="Generate multifunctional GUIs from classes",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="BSD 3-Clause",
    download_url="https://github.com/hanjinliu/magic-class",
    packages=find_packages(exclude=["docs", "examples", "rst"]),
    install_requires=[
          "magicgui>=0.3.2",
          "numpy>=1.20.3",
          "matplotlib>=3.4.2",
          "macro-kit>=0.3.0",
    ],
    python_requires=">=3.7",
    )