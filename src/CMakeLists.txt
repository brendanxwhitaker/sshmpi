cmake_minimum_required(VERSION 2.8.12)
project(mead)

find_package(PythonLibs)
include_directories(${PYTHON_INCLUDE_DIRS})

add_subdirectory(pybind11)
add_subdirectory(srt)
pybind11_add_module(srt mead_srt.cc)
