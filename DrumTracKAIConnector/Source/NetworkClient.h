// NetworkClient.h - Async HTTP client for DrumTracKAI backend
#pragma once
#include <juce_core/juce_core.h>

class DrumTracKAINetworkClient : private juce::Thread
{
public:
    struct Request
    {
        juce::String apiUrl;
        juce::String apiKey;
        double bpm = 120.0;
        juce::String timeSig = "4/4";
        juce::MemoryBlock audioDataWav;  // optional
        juce::MemoryBlock midiDataSMF;   // optional
        juce::String styleId;            // optional
        
        // Guide track support
        bool guideEnabled = false;
        juce::String guideInstrument;    // "mix", "bass", "guitar", "keys", "vocal", "other"
    };

    struct Response
    {
        bool ok = false;
        juce::String statusMessage;
        juce::MemoryBlock midiDataSMF;
    };

    class Listener
    {
    public:
        virtual ~Listener() = default;
        virtual void drumTracKAIRequestFinished (const Response& resp) = 0;
    };

    DrumTracKAINetworkClient();
    ~DrumTracKAINetworkClient() override;

    void setListener (Listener* l) { listener = l; }

    void startRequest (const Request& req);
    bool isBusy() const;

private:
    void run() override;

    Request request;
    Response response;
    std::atomic<bool> hasRequest { false };
    std::atomic<bool> busy { false };
    Listener* listener = nullptr;
};
