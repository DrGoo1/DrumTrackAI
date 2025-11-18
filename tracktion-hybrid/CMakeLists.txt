cmake_minimum_required(VERSION 3.22)
project(DrumTracKAI_Hybrid LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Force MSVC to use the latest standard mode (needed for 'using enum' and other C++20 features)
if (MSVC)
  add_compile_options("/std:c++latest")
endif()

# Add Tracktion Engine directly (it includes JUCE)
# Ensure examples/tests are not added from Tracktion/JUCE
set(TRACKTION_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(TRACKTION_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(JUCE_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(JUCE_BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(TE_ADD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(TRACKTION_DIR "${CMAKE_SOURCE_DIR}/../deps/tracktion_engine")
add_subdirectory("${TRACKTION_DIR}" "${CMAKE_BINARY_DIR}/tracktion_engine")

# Create executable using standard CMake (not juce_add_gui_app)
add_executable(DrumTracKAI_Hybrid WIN32
    cpp/Main.cpp
    cpp/MainComponent.cpp
    cpp/DCSMAdapter.cpp
    cpp/DCSMWaveformComponent.cpp
    cpp/DCSMOrchestrator.cpp
)

# Set target properties
set_target_properties(DrumTracKAI_Hybrid PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)

# Include directories
target_include_directories(DrumTracKAI_Hybrid PRIVATE
    cpp/
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Compile definitions
target_compile_definitions(DrumTracKAI_Hybrid PRIVATE
    JUCE_WEB_BROWSER=0 
    JUCE_USE_CURL=0 
    JUCE_VST3_CAN_REPLACE_VST2=0
    JUCE_MODAL_LOOPS_PERMITTED=1
    JUCE_APPLICATION_NAME_STRING="DrumTracKAI Hybrid"
    JUCE_APPLICATION_VERSION_STRING="1.0.0"
)

# Link with Tracktion Engine (which includes JUCE)
target_link_libraries(DrumTracKAI_Hybrid PRIVATE
    tracktion_engine
)

# Copy Rust FFI DLL next to EXE after build (Windows)
if (WIN32)
  add_custom_command(TARGET DrumTracKAI_Hybrid POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "${CMAKE_SOURCE_DIR}/../tracktion-hybrid/rust/audio-core-ffi/target/release/audio_core_ffi.dll"
      "$<TARGET_FILE_DIR:DrumTracKAI_Hybrid>/audio_core_ffi.dll"
  )
endif()
