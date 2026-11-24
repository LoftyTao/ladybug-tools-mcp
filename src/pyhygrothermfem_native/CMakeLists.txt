cmake_minimum_required(VERSION 3.16)
project(pyhygrothermfem_fairyfly_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

get_filename_component(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." REALPATH)
get_filename_component(VENDOR_ROOT "${REPO_ROOT}/vendor/pyHygroThermFEM-Fairyfly" REALPATH)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

execute_process(
    COMMAND "${Python_EXECUTABLE}" -I -B
        "${CMAKE_CURRENT_SOURCE_DIR}/build_identity.py" configure
        --root "${REPO_ROOT}"
        --header "${CMAKE_BINARY_DIR}/build_source.hxx"
        --identity-file "${CMAKE_BINARY_DIR}/build-source-identity.json"
    RESULT_VARIABLE _build_identity_status
    ERROR_VARIABLE _build_identity_error
)
if(NOT _build_identity_status EQUAL 0)
    message(FATAL_ERROR "Source identity generation failed: ${_build_identity_error}")
endif()

find_package(pybind11 CONFIG REQUIRED)

set(LBNL_LOCAL_SIBLINGS ON CACHE BOOL "Use vendored LBNL dependency sources" FORCE)
set(FETCHCONTENT_FULLY_DISCONNECTED ON CACHE BOOL "Use verified local sources only" FORCE)

function(verified_source_path variable relative_path)
    get_filename_component(_expected "${VENDOR_ROOT}/${relative_path}" REALPATH)
    if(DEFINED ${variable} AND NOT "${${variable}}" STREQUAL "")
        get_filename_component(_actual "${${variable}}" REALPATH BASE_DIR "${VENDOR_ROOT}")
        if(NOT _actual STREQUAL _expected)
            message(FATAL_ERROR "${variable} redirects verified build inputs to '${_actual}'")
        endif()
    endif()
    set(${variable} "${_expected}" CACHE PATH "Verified dependency source" FORCE)
endfunction()

verified_source_path(FETCHCONTENT_SOURCE_DIR_EIGENEXTERNAL vendor/eigen)
verified_source_path(FETCHCONTENT_SOURCE_DIR_KEFFCAVITY vendor/KeffCavity)
verified_source_path(FETCHCONTENT_SOURCE_DIR_LBNLCPPCOMMON vendor/LBNLCPPCommon)
verified_source_path(FETCHCONTENT_SOURCE_DIR_WINDOWSCALC-ENGINE vendor/Windows-CalcEngine)

set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(BUILD_HTFEM_TESTING OFF CACHE BOOL "" FORCE)
set(BUILD_KeffC_TESTING OFF CACHE BOOL "" FORCE)

add_subdirectory("${VENDOR_ROOT}/vendor/HygroThermFEM" "${CMAKE_BINARY_DIR}/vendor/HygroThermFEM")

get_property(_keffcavity_source_dir TARGET KeffCavity PROPERTY SOURCE_DIR)
get_filename_component(_keffcavity_source_dir "${_keffcavity_source_dir}" REALPATH)
get_filename_component(_expected_keffcavity_dir "${VENDOR_ROOT}/vendor/KeffCavity" REALPATH)
if(NOT _keffcavity_source_dir STREQUAL _expected_keffcavity_dir)
    message(FATAL_ERROR
        "KeffCavity target source_dir='${_keffcavity_source_dir}', expected '${_expected_keffcavity_dir}'"
    )
endif()

pybind11_add_module(_native MODULE
    "${VENDOR_ROOT}/bindings/module.cxx"
    "${VENDOR_ROOT}/bindings/steady_solver.cxx"
    "${VENDOR_ROOT}/bindings/transient_solver.cxx"
)
target_include_directories(_native PRIVATE
    "${CMAKE_BINARY_DIR}"
    "${VENDOR_ROOT}/bindings"
)
target_link_libraries(_native PRIVATE HygroThermFEM)
target_compile_features(_native PRIVATE cxx_std_20)

if(NOT CMAKE_LIBRARY_OUTPUT_DIRECTORY)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${REPO_ROOT}/src/pyhygrothermfem_fairyfly")
endif()
set_target_properties(_native PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}"
)
foreach(config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set_target_properties(_native PROPERTIES
        "LIBRARY_OUTPUT_DIRECTORY_${config}" "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}"
        "RUNTIME_OUTPUT_DIRECTORY_${config}" "${CMAKE_LIBRARY_OUTPUT_DIRECTORY}"
    )
endforeach()
