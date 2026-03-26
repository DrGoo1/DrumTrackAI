// NetworkClient.cpp - Async HTTP implementation
#include "NetworkClient.h"
#include "MidiUtils.h"

using namespace juce;

DrumTracKAINetworkClient::DrumTracKAINetworkClient()
    : Thread ("DrumTracKAI Network Thread")
{
    startThread();
}

DrumTracKAINetworkClient::~DrumTracKAINetworkClient()
{
    signalThreadShouldExit();
    stopThread (4000);
}

void DrumTracKAINetworkClient::startRequest (const Request& r)
{
    if (busy.load())
        return;

    request = r;
    hasRequest.store (true);
}

bool DrumTracKAINetworkClient::isBusy() const
{
    return busy.load();
}

void DrumTracKAINetworkClient::run()
{
    while (! threadShouldExit())
    {
        if (! hasRequest.load())
        {
            wait (100);
            continue;
        }

        busy.store (true);
        hasRequest.store (false);
        Response resp;

        // --- Build JSON payload for DrumTracKAI backend ---
        var json;
        json["api_key"]   = request.apiKey;
        json["mode"]      = request.audioDataWav.getSize() > 0 ? var ("audio") : var ("midi");
        json["bpm"]       = request.bpm;
        json["time_sig"]  = request.timeSig;
        
        if (request.styleId.isNotEmpty())
            json["style_id"] = request.styleId;
        
        // Guide track support
        json["guide_enabled"] = request.guideEnabled;
        if (request.guideInstrument.isNotEmpty())
            json["guide_instrument"] = request.guideInstrument;

        if (request.audioDataWav.getSize() > 0)
        {
            String b64 = request.audioDataWav.toBase64Encoding();
            json["audio_wav_base64"] = b64;
        }

        if (request.midiDataSMF.getSize() > 0)
        {
            String b64 = MidiUtils::toBase64 (request.midiDataSMF);
            json["midi_smf_base64"] = b64;
        }

        auto jsonStr = JSON::toString (json);

        // --- HTTP POST ---
        URL url (request.apiUrl);

        StringPairArray headers;
        headers.set ("Content-Type", "application/json");

        auto options = URL::InputStreamOptions (URL::ParameterHandling::inPostData)
                            .withExtraHeaders (headers)
                            .withNumRedirectsToFollow (5)
                            .withConnectionTimeoutMs (30000);

        std::unique_ptr<InputStream> in (url.createInputStream (options.withPOSTData (jsonStr)));

        if (in == nullptr)
        {
            resp.ok = false;
            resp.statusMessage = "HTTP connection failed - check server URL";
        }
        else
        {
            auto resultStr = in->readEntireStreamAsString();
            auto resultVar = JSON::parse (resultStr);

            if (resultVar.isObject())
            {
                auto* obj = resultVar.getDynamicObject();
                bool okFlag = obj->getProperty ("ok");
                resp.ok = okFlag;

                resp.statusMessage = obj->getProperty ("status_message").toString();

                String midiB64 = obj->getProperty ("midi_smf_base64").toString();
                if (midiB64.isNotEmpty())
                {
                    MidiUtils::fromBase64 (midiB64, resp.midiDataSMF);
                }
            }
            else
            {
                resp.ok = false;
                resp.statusMessage = "Bad JSON from server: " + resultStr.substring (0, 100);
            }
        }

        if (listener != nullptr)
        {
            // Call back on message thread
            auto respCopy = resp;
            MessageManager::callAsync ([this, respCopy]() {
                if (listener != nullptr)
                    listener->drumTracKAIRequestFinished (respCopy);
            });
        }

        busy.store (false);
    }
}
