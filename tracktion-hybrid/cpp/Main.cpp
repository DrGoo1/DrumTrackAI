#include <juce_gui_basics/juce_gui_basics.h>
#include "MainComponent.h"

namespace ProjectInfo
{
    const char* const  projectName    = "DrumTracKAI Hybrid";
    const char* const  companyName    = "DrumTracKAI";
    const char* const  versionString  = "1.2.0";
    const int          versionNumber  = 0x10200;
}

// Global application properties for saving preferences
static juce::ApplicationProperties gAppProperties;
juce::PropertiesFile* getAppProperties()
{
    return gAppProperties.getUserSettings();
}

class TracktionHybridApplication : public juce::JUCEApplication
{
public:
    TracktionHybridApplication() {}

    const juce::String getApplicationName() override       { return ProjectInfo::projectName; }
    const juce::String getApplicationVersion() override    { return ProjectInfo::versionString; }
    bool moreThanOneInstanceAllowed() override             { return true; }

    void initialise(const juce::String& commandLine) override
    {
        // Configure ApplicationProperties storage
        juce::PropertiesFile::Options opts;
        opts.applicationName     = ProjectInfo::projectName;
        opts.filenameSuffix      = "settings";
        opts.osxLibrarySubFolder = "Application Support";
        opts.ignoreCaseOfKeyNames = true;
        opts.storageFormat       = juce::PropertiesFile::storeAsXML;
        gAppProperties.setStorageParameters(opts);

        mainWindow.reset(new MainWindow(getApplicationName()));
    }

    void shutdown() override
    {
        mainWindow = nullptr;
    }

    void systemRequestedQuit() override
    {
        quit();
    }

    void anotherInstanceStarted(const juce::String& commandLine) override
    {
    }

    class MainWindow : public juce::DocumentWindow
    {
    public:
        MainWindow(juce::String name)
            : DocumentWindow(name,
                           juce::Desktop::getInstance().getDefaultLookAndFeel()
                                                      .findColour(juce::ResizableWindow::backgroundColourId),
                           DocumentWindow::allButtons)
        {
            setUsingNativeTitleBar(true);
            setContentOwned(new MainComponent(), true);

           #if JUCE_IOS || JUCE_ANDROID
            setFullScreen(true);
           #else
            setResizable(true, true);
            centreWithSize(getContentComponent()->getWidth(), getContentComponent()->getHeight());
           #endif

            setVisible(true);
        }

        void closeButtonPressed() override
        {
            JUCEApplication::getInstance()->systemRequestedQuit();
        }

    private:
        JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MainWindow)
    };

private:
    std::unique_ptr<MainWindow> mainWindow;
};

START_JUCE_APPLICATION(TracktionHybridApplication)
