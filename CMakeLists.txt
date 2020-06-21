cmake_minimum_required(VERSION 2.8.12)
set(CMAKE_CXX_STANDARD 17)
project(mead)

find_package(PythonLibs)
include_directories(${PYTHON_INCLUDE_DIRS})

include(ExternalProject)
ExternalProject_Add(project_srt
        GIT_REPOSITORY https://github.com/ethouris/srt.git
        GIT_TAG dev-fix-attributes
        UPDATE_COMMAND ""
        SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/srt
        BINARY_DIR ${CMAKE_CURRENT_SOURCE_DIR}/srt
        CONFIGURE_COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/srt/configure
        GIT_SUBMODULES ""
        BUILD_COMMAND make srt_static
        GIT_PROGRESS 1
        STEP_TARGETS build
        EXCLUDE_FROM_ALL TRUE
        INSTALL_COMMAND ""
        )
add_library(srt STATIC IMPORTED)
set_property(TARGET srt PROPERTY IMPORTED_LOCATION ${CMAKE_CURRENT_SOURCE_DIR}/srt/libsrt.a)
find_package (Threads REQUIRED)
find_package(OpenSSL REQUIRED)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/srt/)

add_subdirectory(lib/pybind11)

pybind11_add_module(mead_srt src/mead_srt.cc)
add_dependencies(mead_srt pybind11::module project_srt)
target_link_libraries(mead_srt PRIVATE pybind11::module srt ${OPENSSL_LIBRARIES} Threads::Threads)
