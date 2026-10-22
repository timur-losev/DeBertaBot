# decider_eval (research only): a decider GGUF on llama.cpp, with the bot's own llama.cpp build (b11429, laid out by
# cpp/coop_intent/tools/setup_llama.ps1) and nlohmann/json from cpp/coop_intent/third_party.
#   cmake -S . -B build -G "Visual Studio 17 2022" -A x64 && cmake --build build --config Release
cmake_minimum_required(VERSION 3.20)
project(decider_eval CXX)
set(CMAKE_CXX_STANDARD 17)
set(COOP "${CMAKE_CURRENT_SOURCE_DIR}/../../../../cpp/coop_intent")
set(LLAMA_DIR "${COOP}/third_party/llama.cpp-b11429-win-x64")
add_executable(decider_eval decider_eval.cpp)
target_include_directories(decider_eval PRIVATE "${LLAMA_DIR}/include" "${COOP}/third_party")
target_compile_definitions(decider_eval PRIVATE LLAMA_SHARED GGML_SHARED)
target_link_libraries(decider_eval PRIVATE "${LLAMA_DIR}/lib/llama.lib")
if(MSVC)
  target_compile_options(decider_eval PRIVATE /utf-8 /O2)
endif()
file(GLOB LLAMA_DLLS "${LLAMA_DIR}/bin/*.dll")
add_custom_command(TARGET decider_eval POST_BUILD COMMAND ${CMAKE_COMMAND} -E copy_if_different ${LLAMA_DLLS} $<TARGET_FILE_DIR:decider_eval>)
