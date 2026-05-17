import setuptools
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "hive_bus",
        ["jarvis/cpp/hive_bus.cpp"],
    ),
]

setuptools.setup(
    name="hive_bus",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
