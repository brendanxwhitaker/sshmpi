cmake_minimum_required(VERSION 2.8.12)
project(mead)

find_package(PythonLibs)
include_directories(${PYTHON_INCLUDE_DIRS})

add_subdirectory(lib/pybind11)
add_subdirectory(lib/srt)
pybind11_add_module(srt src/mead_srt.cc)
