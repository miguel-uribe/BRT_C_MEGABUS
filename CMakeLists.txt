cmake_minimum_required(VERSION 3.18)
project(brt_simulator LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Run cmake through `uv run` so that the interpreter of the project environment is found.
find_package(Python 3.12 COMPONENTS Interpreter Development.Module REQUIRED)

# pybind11 is installed as a Python package, we ask it where its CMake files are.
if(NOT pybind11_DIR)
    execute_process(
        COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
        OUTPUT_VARIABLE pybind11_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE pybind11_cmakedir_result
    )
    if(NOT pybind11_cmakedir_result EQUAL 0)
        message(FATAL_ERROR "pybind11 was not found in ${Python_EXECUTABLE}. Run `uv sync` first.")
    endif()
endif()
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(simulator MODULE src_cpp/main.cpp)

if(MINGW)
    # The module must not depend on the MinGW runtime DLLs, Python would not find them.
    target_link_options(simulator PRIVATE -static -static-libgcc -static-libstdc++)
endif()

# The module is written next to the sources, where the Python scripts look for it.
set_target_properties(simulator PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src_cpp"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/src_cpp"
    LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}/src_cpp"
    LIBRARY_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_CURRENT_SOURCE_DIR}/src_cpp"
)
