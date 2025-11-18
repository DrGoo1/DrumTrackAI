#NoEnv
#SingleInstance Force
SendMode Input
SetTitleMatchMode, 2

; Advanced Render Button Clicker for REAPER
; Uses multiple detection and clicking methods

; Log function
WriteLog(message) {
    FileAppend, %A_Hour%:%A_Min%:%A_Sec% - %message%`n, render_clicker_log.txt
}

; Main function
ClickRenderButton() {
    WriteLog("Starting Advanced Render Button Clicker")
    
    ; Method 1: Find window by title and use ControlClick
    WriteLog("Method 1: Looking for render window...")
    
    ; Try different window titles
    WindowTitles := ["Render", "Render to File", "REAPER"]
    
    Loop % WindowTitles.Length() {
        title := WindowTitles[A_Index]
        WriteLog("Checking for window: " . title)
        
        WinWait, %title%,, 2
        if ErrorLevel {
            WriteLog("Window not found: " . title)
            continue
        }
        
        WriteLog("Found window: " . title)
        WinActivate, %title%
        WinWaitActive, %title%,, 2
        
        ; Try to find and click render button using control names
        WriteLog("Trying ControlClick methods...")
        
        ; Common button control names in Windows dialogs
        ButtonControls := ["Button1", "Button2", "Button3", "Button4", "&Render", "Render", "OK"]
        
        Loop % ButtonControls.Length() {
            control := ButtonControls[A_Index]
            WriteLog("Trying ControlClick on: " . control)
            
            ControlClick, %control%, %title%
            Sleep, 500
            
            ; Check if window closed (indicating successful click)
            WinWait, %title%,, 1
            if ErrorLevel {
                WriteLog("SUCCESS: Window closed after clicking " . control)
                return true
            }
        }
    }
    
    ; Method 2: Use window coordinates and calculated positions
    WriteLog("Method 2: Using coordinate-based clicking...")
    
    ; Find any REAPER-related window
    WinGet, windows, List, REAPER
    Loop %windows% {
        id := windows%A_Index%
        WinGetTitle, title, ahk_id %id%
        WriteLog("Found REAPER window: " . title)
        
        ; Get window position and size
        WinGetPos, x, y, w, h, ahk_id %id%
        WriteLog("Window position: " . x . "," . y . " Size: " . w . "x" . h)
        
        ; Activate window
        WinActivate, ahk_id %id%
        WinWaitActive, ahk_id %id%,, 2
        
        ; Calculate likely button positions (bottom-right area of dialog)
        buttonX1 := x + w - 100
        buttonY1 := y + h - 40
        
        buttonX2 := x + w - 180
        buttonY2 := y + h - 40
        
        buttonX3 := x + w/2 + 50
        buttonY3 := y + h - 60
        
        ; Try clicking these positions
        positions := [[buttonX1, buttonY1], [buttonX2, buttonY2], [buttonX3, buttonY3]]
        
        Loop % positions.Length() {
            pos := positions[A_Index]
            clickX := pos[1]
            clickY := pos[2]
            
            WriteLog("Clicking position: " . clickX . "," . clickY)
            
            ; Move mouse and click
            MouseMove, %clickX%, %clickY%, 0
            Sleep, 200
            Click, %clickX%, %clickY%
            Sleep, 500
            
            ; Check if window still exists
            WinWait, ahk_id %id%,, 1
            if ErrorLevel {
                WriteLog("SUCCESS: Window closed after clicking position " . A_Index)
                return true
            }
        }
    }
    
    ; Method 3: Keyboard shortcuts
    WriteLog("Method 3: Trying keyboard shortcuts...")
    
    ; Send various key combinations that might trigger render
    keys := ["Enter", "Space", "{Tab}{Enter}", "{Tab}{Tab}{Enter}", "r", "!r"]
    
    Loop % keys.Length() {
        key := keys[A_Index]
        WriteLog("Sending key: " . key)
        
        Send, %key%
        Sleep, 1000
    }
    
    ; Method 4: Send Alt+R (if it's a menu shortcut)
    WriteLog("Method 4: Trying Alt+R shortcut...")
    Send, !r
    Sleep, 1000
    
    WriteLog("All methods completed")
    return false
}

; Main execution
MsgBox, 4, Advanced Render Clicker, Make sure REAPER render dialog is open, then click YES to start clicking tests.
IfMsgBox Yes
{
    result := ClickRenderButton()
    if (result) {
        MsgBox, SUCCESS: Render button was clicked!
    } else {
        MsgBox, All clicking methods attempted. Check render_clicker_log.txt for details.
    }
}

ExitApp
