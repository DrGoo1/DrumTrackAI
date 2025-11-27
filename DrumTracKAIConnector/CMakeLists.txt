cmake_minimum_required(VERSION 3.15)

project(DrumTracKAIConnector VERSION 1.0.0)

# JUCE setup - assumes JUCE is in parent directory or as submodule
set(JUCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../deps/JUCE" CACHE PATH "Path to JUCE")

if(NOT EXISTS "${JUCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "JUCE not found at ${JUCE_DIR}. Please clone JUCE or set JUCE_DIR")
endif()

add_subdirectory(${JUCE_DIR} JUCE_build)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

juce_add_plugin(DrumTracKAIConnector
    COMPANY_NAME "Umbo Gumbo LLC"
    BUNDLE_ID com.umbogumbo.drumtrackai.connector
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT TRUE
    IS_MIDI_EFFECT TRUE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD TRUE

    # Formats - Windows supports VST3, macOS supports VST3 and AU
    VST3 TRUE
    AU $<$<PLATFORM_ID:Darwin>:TRUE>
    AUv3 FALSE
    AAX FALSE
    Standalone TRUE  # Include standalone for testing

    PLUGIN_MANUFACTURER_CODE Umbg
    PLUGIN_CODE Dtka
    FORMATS VST3 Standalone

    PRODUCT_NAME "DrumTracKAI Connector"
)

target_sources(DrumTracKAIConnector
    PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginProcessor.h
        Source/PluginEditor.cpp
        Source/PluginEditor.h
        Source/NetworkClient.cpp
        Source/NetworkClient.h
        Source/MidiUtils.cpp
        Source/MidiUtils.h
)

target_compile_definitions(DrumTracKAIConnector
    PUBLIC
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=1
        JUCE_VST3_CAN_REPLACE_VST2=0
        JUCE_DISPLAY_SPLASH_SCREEN=0
        JUCE_REPORT_APP_USAGE=0
)

target_link_libraries(DrumTracKAIConnector
    PRIVATE
        juce::juce_audio_utils
        juce::juce_audio_devices
        juce::juce_audio_processors
        juce::juce_audio_basics
        juce::juce_core
        juce::juce_data_structures
        juce::juce_events
        juce::juce_graphics
        juce::juce_gui_basics
        juce::juce_gui_extra
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags
)
