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
# the default bot (scripts/coop/bots.py names the same one for the Python tools). Weights are not in git:
# on a machine without the default bot's, coop_cli defaults to the v2 bot. A cache variable: pass
# -DCOOP_MODEL_DIR=... or use coop_cli --model-dir for another bot
set(_COOP_BOT "${CMAKE_CURRENT_SOURCE_DIR}/../../models/coop-deberta-v3-ens3-v31/cpp")
if(NOT EXISTS "${_COOP_BOT}/model0.onnx")
  message(STATUS "the weights of the default bot (coop-deberta-v3-ens3-v31) are not on this machine: coop_cli defaults to coop-deberta-v3-ens3-v2")
  set(_COOP_BOT "${CMAKE_CURRENT_SOURCE_DIR}/../../models/coop-deberta-v3-ens3-v2/cpp")
endif()
set(COOP_MODEL_DIR "${_COOP_BOT}" CACHE PATH "export_cpp.py output")
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
  src/intent_model.cpp
  src/speech_text.cpp)
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
else()
  # macOS / Linux: the executable finds the runtime library where it was linked from
  set_target_properties(coop_cli PROPERTIES BUILD_RPATH "${ORT_DIR}/lib")
endif()

# Speech-to-text, optional: sherpa-onnx's C API (include/sherpa-onnx/c-api/c-api.h, lib/sherpa-onnx-c-api.*,
# lib/onnxruntime.dll) under third_party/. The Python package `sherpa-onnx` of the same version carries
# exactly these files (site-packages/sherpa_onnx/include and lib), so the C++ and the Python transcripts
# come from one binary.
#
# A process holds ONE onnxruntime.dll, and the transcripts depend on which: on sherpa-onnx's own runtime
# (1.28.2 for sherpa-onnx 1.13.8) the C++ transcripts equal the Python ones clip for clip; on the engine's
# 1.30.0 they differ on 3% of clean clips and 20-30% of accented ones (README.md, "Speech-to-text"). The
# bots were trained on the Python transcripts, so with speech-to-text the exe gets sherpa-onnx's runtime,
# and the engine runs the bot on it too (ort_backend.cpp asks the loaded runtime for its own API level).
#
# macOS loads a library by its path, not by its name, so there the process holds both: sherpa-onnx's library
# takes the libonnxruntime.dylib next to it (the same 1.28.2), and the bot stays on the engine's runtime.
if(WIN32)
  set(SHERPA_NAME "sherpa-onnx-1.13.8-win-x64")
  set(SHERPA_LIB "lib/sherpa-onnx-c-api.lib")
elseif(APPLE)
  set(SHERPA_NAME "sherpa-onnx-1.13.8-osx")
  set(SHERPA_LIB "lib/libsherpa-onnx-c-api.dylib")
else()
  set(SHERPA_NAME "sherpa-onnx-1.13.8-linux")
  set(SHERPA_LIB "lib/libsherpa-onnx-c-api.so")
endif()
set(SHERPA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/${SHERPA_NAME}" CACHE PATH "sherpa-onnx C API (include/, lib/)")
set(COOP_STT_MODEL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../scripts/coop/stt/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
    CACHE PATH "sherpa-onnx export of Parakeet TDT 0.6B v2 (scripts/coop/stt/README.md)")
if(EXISTS "${SHERPA_DIR}/include/sherpa-onnx/c-api/c-api.h" AND EXISTS "${SHERPA_DIR}/${SHERPA_LIB}")
  add_library(coop_intent_stt STATIC src/sherpa_speech.cpp)
  target_include_directories(coop_intent_stt PRIVATE "${SHERPA_DIR}/include")
  target_link_libraries(coop_intent_stt PUBLIC coop_intent_core "${SHERPA_DIR}/${SHERPA_LIB}")
  target_link_libraries(coop_cli PRIVATE coop_intent_stt)
  get_filename_component(COOP_STT_MODEL_DIR_ABS "${COOP_STT_MODEL_DIR}" ABSOLUTE)
  target_compile_definitions(coop_cli PRIVATE COOP_WITH_STT COOP_DEFAULT_STT_DIR="${COOP_STT_MODEL_DIR_ABS}")
  if(WIN32)
    target_sources(coop_cli PRIVATE tools/mic_capture_win.cpp)   # the microphone of coop_cli --voice
    target_link_libraries(coop_cli PRIVATE winmm)
    add_custom_command(TARGET coop_cli POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SHERPA_DIR}/lib/sherpa-onnx-c-api.dll" $<TARGET_FILE_DIR:coop_cli>)
    if(EXISTS "${SHERPA_DIR}/lib/onnxruntime.dll")
      set(COOP_RUNTIME_DLLS "${SHERPA_DIR}/lib/onnxruntime.dll")
      message(STATUS "speech-to-text: coop_cli runs on sherpa-onnx's ONNX Runtime (${SHERPA_DIR}/lib/onnxruntime.dll)")
    else()
      message(STATUS "speech-to-text: no onnxruntime.dll in ${SHERPA_DIR}/lib, the recognizer runs on the engine's ONNX Runtime: its transcripts differ from the Python package's")
    endif()
  elseif(APPLE)
    # the microphone of coop_cli --voice: an AudioQueue, AVFoundation for the permission macOS asks the user
    # for, and CoreGraphics for the state of the talk key (a terminal reports no key-up)
    enable_language(OBJCXX)
    target_sources(coop_cli PRIVATE tools/mic_capture_mac.mm)
    set_source_files_properties(tools/mic_capture_mac.mm PROPERTIES COMPILE_OPTIONS "-fobjc-arc")
    set_target_properties(coop_cli PROPERTIES OBJCXX_STANDARD 17 OBJCXX_STANDARD_REQUIRED ON)
    target_link_libraries(coop_cli PRIVATE "-framework AudioToolbox" "-framework CoreAudio" "-framework AVFoundation"
                          "-framework Foundation" "-framework CoreGraphics" "-framework CoreFoundation")
    # sherpa-onnx's directory first: the engine's also holds a file called libonnxruntime.dylib (1.30.0), and
    # sherpa-onnx's library must not be given that one
    set_property(TARGET coop_cli PROPERTY BUILD_RPATH "${SHERPA_DIR}/lib" "${ORT_DIR}/lib")
    if(EXISTS "${SHERPA_DIR}/lib/libonnxruntime.dylib")
      message(STATUS "speech-to-text: the recognizer runs on sherpa-onnx's ONNX Runtime (${SHERPA_DIR}/lib/libonnxruntime.dylib), the bot on the engine's")
    else()
      message(STATUS "speech-to-text: no libonnxruntime.dylib in ${SHERPA_DIR}/lib, the recognizer runs on the engine's ONNX Runtime: its transcripts differ from the Python package's")
    endif()
  else()
    set_property(TARGET coop_cli APPEND PROPERTY BUILD_RPATH "${SHERPA_DIR}/lib")
  endif()
else()
  message(STATUS "sherpa-onnx is not in ${SHERPA_DIR}: coop_cli is built without speech-to-text (--voice, --stt-wav, --stt-tests)")
endif()

if(WIN32)
  # the runtime next to the exe: Windows ships an older onnxruntime.dll in System32 that must not be picked up.
  # A leftover onnxruntime_providers_shared.dll of another version is removed: only the CPU provider is used
  if(NOT COOP_RUNTIME_DLLS)
    set(COOP_RUNTIME_DLLS "${ORT_DIR}/lib/onnxruntime.dll" "${ORT_DIR}/lib/onnxruntime_providers_shared.dll")
  else()
    add_custom_command(TARGET coop_cli POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E rm -f "$<TARGET_FILE_DIR:coop_cli>/onnxruntime_providers_shared.dll")
  endif()
  add_custom_command(TARGET coop_cli POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${COOP_RUNTIME_DLLS} $<TARGET_FILE_DIR:coop_cli>)
endif()
