#include "RustCoreBridge.h"
#include <iostream>

RustCoreBridge::RustCoreBridge() : lib(nullptr) {}

RustCoreBridge::~RustCoreBridge() {
    if (lib) {
        juce::DynamicLibrary::close(lib);
    }
}

bool RustCoreBridge::load(const juce::File& dylib) {
    if (!dylib.exists()) {
        juce::Logger::writeToLog("FFI library not found: " + dylib.getFullPathName());
        return false;
    }
    
    lib = juce::DynamicLibrary::open(dylib.getFullPathName());
    if (!lib) {
        juce::Logger::writeToLog("Failed to load FFI library: " + dylib.getFullPathName());
        return false;
    }
    
    // Load function pointers
    ac_peaks = (ac_peaks_fn) juce::DynamicLibrary::getFunction(lib, "ac_peaks");
    ac_analyze = (ac_analyze_fn) juce::DynamicLibrary::getFunction(lib, "ac_analyze");
    ac_sectionize_smart = (ac_sectionize_smart_fn) juce::DynamicLibrary::getFunction(lib, "ac_sectionize_smart");
    ac_generate_json = (ac_generate_json_fn) juce::DynamicLibrary::getFunction(lib, "ac_generate_json");
    ac_generate_midi64 = (ac_generate_midi64_fn) juce::DynamicLibrary::getFunction(lib, "ac_generate_midi64");
    ac_free = (ac_free_fn) juce::DynamicLibrary::getFunction(lib, "ac_free");
    ac_last_error = (ac_last_error_fn) juce::DynamicLibrary::getFunction(lib, "ac_last_error");
    
    if (!ac_peaks || !ac_analyze || !ac_sectionize_smart || !ac_generate_json || !ac_generate_midi64 || !ac_free || !ac_last_error) {
        juce::Logger::writeToLog("Failed to load all FFI functions");
        juce::DynamicLibrary::close(lib);
        lib = nullptr;
        return false;
    }
    
    juce::Logger::writeToLog("FFI library loaded successfully: " + dylib.getFullPathName());
    return true;
}

juce::var RustCoreBridge::peaks(const juce::File& audio) {
    if (!lib || !ac_peaks) return juce::var();
    
    auto path = audio.getFullPathName().toUTF8();
    char* result = ac_peaks(path);
    
    if (result) {
        juce::String jsonStr(result);
        ac_free(result);
        
        auto parsed = juce::JSON::parse(jsonStr);
        return parsed.wasOk() ? parsed.getResult() : juce::var();
    }
    
    return juce::var();
}

juce::var RustCoreBridge::analyze(const juce::File& audio) {
    if (!lib || !ac_analyze) return juce::var();
    
    auto path = audio.getFullPathName().toUTF8();
    char* result = ac_analyze(path);
    
    if (result) {
        juce::String jsonStr(result);
        ac_free(result);
        
        auto parsed = juce::JSON::parse(jsonStr);
        return parsed.wasOk() ? parsed.getResult() : juce::var();
    }
    
    return juce::var();
}

juce::var RustCoreBridge::sectionizeSmart(const juce::File& audio, float bpm, int minBars, int maxBars) {
    if (!lib || !ac_sectionize_smart) return juce::var();
    
    auto path = audio.getFullPathName().toUTF8();
    char* result = ac_sectionize_smart(path, bpm, minBars, maxBars);
    
    if (result) {
        juce::String jsonStr(result);
        ac_free(result);
        
        auto parsed = juce::JSON::parse(jsonStr);
        return parsed.wasOk() ? parsed.getResult() : juce::var();
    }
    
    return juce::var();
}

juce::var RustCoreBridge::generateNotes(const juce::var& params) {
    if (!lib || !ac_generate_json) return juce::var();
    
    auto jsonStr = juce::JSON::toString(params);
    auto jsonUtf8 = jsonStr.toUTF8();
    char* result = ac_generate_json(jsonUtf8);
    
    if (result) {
        juce::String resultStr(result);
        ac_free(result);
        
        auto parsed = juce::JSON::parse(resultStr);
        return parsed.wasOk() ? parsed.getResult() : juce::var();
    }
    
    return juce::var();
}

juce::var RustCoreBridge::generateMidi64(const juce::var& params) {
    if (!lib || !ac_generate_midi64) return juce::var();
    
    auto jsonStr = juce::JSON::toString(params);
    auto jsonUtf8 = jsonStr.toUTF8();
    char* result = ac_generate_midi64(jsonUtf8);
    
    if (result) {
        juce::String resultStr(result);
        ac_free(result);
        
        juce::var obj = new juce::DynamicObject();
        obj.getObject()->setProperty("midi_base64", resultStr);
        return obj;
    }
    
    return juce::var();
}

juce::String RustCoreBridge::getLastError() {
    if (!lib || !ac_last_error) return "FFI library not loaded";
    
    char* error = ac_last_error();
    if (error) {
        juce::String errorStr(error);
        return errorStr;
    }
    
    return "No error";
}
