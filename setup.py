#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple check list from AllenNLP repo:
https://github.com/allenai/allennlp/blob/master/setup.py

To create the package for pypi.

1.  Change the version in __init__.py, setup.py as well as docs/source/conf.py.

2.  Commit these changes with the message: "Release: VERSION"

3.  Add a tag in git to mark the release:
        git tag VERSION -m 'Adds tag VERSION for pypi'

    Push the tag to git:
        git push --tags origin master

4.  Build both the sources and the wheel.

    Do not change anything in setup.py between creating the wheel and the
    source distribution (obviously).

    For the wheel, run: "python setup.py bdist_wheel" in the top level
    directory.  (this will build a wheel for the python version you use to
    build it).

    For the sources, run: "python setup.py sdist" You should now have a /dist
    directory with both .whl and .tar.gz source versions.

5.  Check that everything looks correct by uploading package to test server:

    twine upload dist/* -r pypitest

    (pypi suggest using twine as other methods upload files via plaintext.)

    You may have to specify the repository url,
    use the following command then:
        twine upload dist/* -r pypitest\
        --repository-url=https://test.pypi.org/legacy/

    Check that you can install it in a virtualenv by running:
        pip install -i https://testpypi.python.org/pypi transformers

6.  Upload the final version to actual pypi:

    twine upload dist/* -r pypi

7.  Copy the release notes from RELEASE.md to the tag in github.

"""
import os
import re
import sys
import sysconfig
import platform
import subprocess

from distutils.version import LooseVersion
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.test import test as TestCommand
from shutil import copyfile, copymode


class CMakeExtension(Extension):
    def __init__(self, name, dependencies, sourcedir=""):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)
        self.dependencies = dependencies


class CMakeBuild(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: "
                + ", ".join(e.name for e in self.extensions)
            )

        if platform.system() == "Windows":
            cmake_version = LooseVersion(
                re.search(r"version\s*([\d.]+)", out.decode()).group(1)
            )
            if cmake_version < "3.1.0":
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):

        # Clone the dependencies.
        if not os.path.isdir("lib/"):
            os.path.mkdir("lib/")
        for name, url in ext.dependencies.items():
            command = "if cd %s; then git pull; else git clone %s; fi" % (name, url)
            out = subprocess.check_output(command, shell=True, cwd="lib")
            print("out:", out)

        print("Dependencies cloned.")

        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = [
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + extdir,
            "-DPYTHON_EXECUTABLE=" + sys.executable,
        ]

        cfg = "Debug" if self.debug else "Release"
        build_args = ["--config", cfg]

        if platform.system() == "Windows":
            cmake_args += [
                "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), extdir)
            ]
            if sys.maxsize > 2 ** 32:
                cmake_args += ["-A", "x64"]
            build_args += ["--", "/m"]
        else:
            cmake_args += ["-DCMAKE_BUILD_TYPE=" + cfg]
            build_args += ["--", "-j2"]

        env = os.environ.copy()
        env["CXXFLAGS"] = '{} -DVERSION_INFO=\\"{}\\"'.format(
            env.get("CXXFLAGS", ""), self.distribution.get_version()
        )
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(
            ["cmake", ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env
        )
        subprocess.check_call(
            ["cmake", "--build", "."] + build_args, cwd=self.build_temp
        )

        print()  # Add an empty line for cleaner output


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname: str) -> str:
    """ Read and return README as str. """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="mead-mpi",
    version="0.0.1a",
    author="Brendan Whitaker",
    description=("A message passing interface via UDP NAT-traversal."),
    license="GPLv3",
    packages=["mead"],
    long_description="",
    long_description_content_type="text/plain",
    install_requires=["numpy", "parallel-ssh", "paramiko", "dill"],
    scripts=["bin/clonemead", "bin/meadclient", "bin/update_hostsfile"],
    package_data={"mead": []},
    include_package_data=True,
    python_requires=">=3.7.0",
    ext_modules=[
        CMakeExtension(
            "mead/srt",
            dependencies={
                "srt": "https://github.com/haivision/srt.git",
                "pybind11": "https://github.com/pybind/pybind11.git",
            },
        )
    ],
    cmdclass=dict(build_ext=CMakeBuild),
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python :: 3.7",
    ],
)
