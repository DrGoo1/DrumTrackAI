#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class PreferencesComponent : public juce::Component
{
public:
    struct Callbacks {
        std::function<void(const juce::File& exportDir, const juce::File& ffiPath)> onApply;
    };

    explicit PreferencesComponent(juce::PropertiesFile* props, Callbacks cb = {})
        : properties(props), callbacks(std::move(cb))
    {
        addAndMakeVisible(exportDirLabel);
        exportDirLabel.setText("MIDI Export Folder", juce::dontSendNotification);

        addAndMakeVisible(exportDirEditor);
        exportDirEditor.setText(properties ? properties->getValue("exportDir") : juce::String());
        exportDirEditor.setReadOnly(true);

        addAndMakeVisible(exportDirBrowse);
        exportDirBrowse.setButtonText("Browse...");
        exportDirBrowse.onClick = [this] { browseForDir(exportDirEditor); };

        addAndMakeVisible(ffiPathLabel);
        ffiPathLabel.setText("audio_core_ffi DLL", juce::dontSendNotification);

        addAndMakeVisible(ffiPathEditor);
        ffiPathEditor.setText(properties ? properties->getValue("ffiPath") : juce::String());
        ffiPathEditor.setReadOnly(true);

        addAndMakeVisible(ffiPathBrowse);
        ffiPathBrowse.setButtonText("Browse...");
        ffiPathBrowse.onClick = [this] { browseForFile(ffiPathEditor); };

        addAndMakeVisible(applyButton);
        applyButton.setButtonText("Apply");
        applyButton.onClick = [this] { apply(); };
    }

    void resized() override
    {
        auto area = getLocalBounds().reduced(12);
        auto rowH = 28;

        exportDirLabel.setBounds(area.removeFromTop(rowH));
        {
            auto row = area.removeFromTop(rowH);
            exportDirEditor.setBounds(row.removeFromLeft(row.getWidth() - 100));
            exportDirBrowse.setBounds(row);
        }
        area.removeFromTop(8);

        ffiPathLabel.setBounds(area.removeFromTop(rowH));
        {
            auto row = area.removeFromTop(rowH);
            ffiPathEditor.setBounds(row.removeFromLeft(row.getWidth() - 100));
            ffiPathBrowse.setBounds(row);
        }
        area.removeFromTop(12);

        applyButton.setBounds(area.removeFromTop(rowH));
    }

private:
    void browseForDir(juce::TextEditor& editor)
    {
        juce::FileChooser chooser("Select export folder", juce::File(editor.getText()), "");
        if (chooser.browseForDirectory())
            editor.setText(chooser.getResult().getFullPathName());
    }

    void browseForFile(juce::TextEditor& editor)
    {
        juce::FileChooser chooser("Select audio_core_ffi.dll", juce::File(editor.getText()), "*.dll;*.dylib;*.so");
        if (chooser.browseForFileToOpen())
            editor.setText(chooser.getResult().getFullPathName());
    }

    void apply()
    {
        if (properties)
        {
            properties->setValue("exportDir", exportDirEditor.getText());
            properties->setValue("ffiPath", ffiPathEditor.getText());
            properties->saveIfNeeded();
        }

        if (callbacks.onApply)
            callbacks.onApply(juce::File(exportDirEditor.getText()), juce::File(ffiPathEditor.getText()));
    }

    juce::PropertiesFile* properties;
    Callbacks callbacks;

    juce::Label exportDirLabel, ffiPathLabel;
    juce::TextEditor exportDirEditor, ffiPathEditor;
    juce::TextButton exportDirBrowse, ffiPathBrowse, applyButton;
};
