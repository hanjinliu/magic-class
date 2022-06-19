from setuptools import setup, find_packages

with open("magicclass/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]

with open("README.md") as f:
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
    packages=find_packages(exclude=["docs", "examples", "rst", "tests", "tests.*"]),
    package_data={"magicclass": ["**/*.pyi", "*.pyi"]},
    install_requires=[
        "magicgui>=0.4.0",
        "qtpy>=1.10.0",
        "macro-kit>=0.3.5",
        "superqt>=0.2.5.post1",
    ],
    python_requires=">=3.8",
)
