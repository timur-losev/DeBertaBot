cmake_minimum_required(VERSION 3.20)
project(coop_intent LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ONNX Runtime 1.30.0 release for this platform, unpacked under third_party/ (github.com/microsoft/onnxruntime/releases)
if(WIN32)
  set(ORT_NAME "onnxruntime-win-x64-1.30.0")
elseif(APPLE)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    set(ORT_NAME "onnxruntime-osx-arm64-1.30.0")
  else()
    set(ORT_NAME "onnxruntime-osx-x86_64-1.30.0")
  endif()
else()
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    set(ORT_NAME "onnxruntime-linux-aarch64-1.30.0")
  else()
    set(ORT_NAME "onnxruntime-linux-x64-1.30.0")
  endif()
endif()
set(ORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/${ORT_NAME}" CACHE PATH "ONNX Runtime release (include/, lib/)")
# the shipped bot (scripts/coop/bots.py names the same one for the Python tools); a cache variable:
# pass -DCOOP_MODEL_DIR=... or use coop_cli --model-dir for another bot
set(COOP_MODEL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../models/coop-deberta-v3-ens3-v2/cpp" CACHE PATH "export_cpp.py output")
if(NOT EXISTS "${ORT_DIR}/include/onnxruntime_cxx_api.h")
  message(FATAL_ERROR "ONNX Runtime not found in ${ORT_DIR}: unpack the ${ORT_NAME} release there, or pass -DORT_DIR=<dir>")
endif()

if(MSVC)
  add_compile_options(/utf-8 /W4 /permissive- /EHsc)
endif()
find_package(Threads REQUIRED)

# the engine without the model runtime: tokenizer, bot logic, places, softmax -- what moves into UE5 as is
add_library(coop_intent_core STATIC
  src/unicode.cpp
  src/tokenizer.cpp
  src/bot_brain.cpp
  src/locations.cpp
  src/intent_model.cpp)
target_include_directories(coop_intent_core PUBLIC include)
target_link_libraries(coop_intent_core PUBLIC Threads::Threads)

# the model in ONNX Runtime (UE5 uses NNE instead)
if(WIN32)
  set(ORT_LIB "${ORT_DIR}/lib/onnxruntime.lib")
elseif(APPLE)
  set(ORT_LIB "${ORT_DIR}/lib/libonnxruntime.dylib")
else()
  set(ORT_LIB "${ORT_DIR}/lib/libonnxruntime.so")
endif()
add_library(coop_intent_ort STATIC src/ort_backend.cpp)
target_include_directories(coop_intent_ort PUBLIC "${ORT_DIR}/include")
target_link_libraries(coop_intent_ort PUBLIC coop_intent_core "${ORT_LIB}")

add_executable(coop_cli tools/coop_cli.cpp)
target_include_directories(coop_cli PRIVATE third_party)
target_link_libraries(coop_cli PRIVATE coop_intent_ort)
get_filename_component(COOP_MODEL_DIR_ABS "${COOP_MODEL_DIR}" ABSOLUTE)
target_compile_definitions(coop_cli PRIVATE COOP_DEFAULT_MODEL_DIR="${COOP_MODEL_DIR_ABS}")
if(WIN32)
  target_link_libraries(coop_cli PRIVATE psapi)
  # next to the exe: Windows ships an older onnxruntime.dll in System32 that must not be picked up
  add_custom_command(TARGET coop_cli POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${ORT_DIR}/lib/onnxruntime.dll"
            "${ORT_DIR}/lib/onnxruntime_providers_shared.dll" $<TARGET_FILE_DIR:coop_cli>)
else()
  # macOS / Linux: the executable finds the runtime library where it was linked from
  set_target_properties(coop_cli PROPERTIES BUILD_RPATH "${ORT_DIR}/lib")
endif()
