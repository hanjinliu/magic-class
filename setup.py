import sys

sys.stderr.write(
    """
    =======================================================================
    collections-undo does not support `python setup.py install`. Please use

        $ python -m pip install .

    instead.
    =======================================================================
    """
)
sys.exit(1)


setup(
    name="magic-class",
    description="Generate multifunctional GUIs from classes",
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="BSD 3-Clause",
    download_url="https://github.com/hanjinliu/magic-class",
    packages=find_packages(exclude=["docs", "examples", "rst", "tests", "tests.*"]),
    package_data={"magicclass": ["**/*.pyi", "*.pyi"]},
    install_requires=[
        "magicgui>=0.7.0",
        "qtpy>=1.10.0",
        "macro-kit>=0.4.0",
        "superqt>=0.4.0",
    ],
    tests_require=[
        "pytest",
        "pytest-qt",
        "numpy",
        "pyqt5",
        "pyqtgraph",
        "vispy",
    ],
    python_requires=">=3.8",
)
