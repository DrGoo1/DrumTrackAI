@echo off
echo Cleaning up test files created during audio bug diagnosis...

del /Q "frontend\src\components\MinimalAudioTest.tsx" 2>nul
del /Q "frontend\src\components\WebDAWApp_Minimal.tsx" 2>nul
del /Q "frontend\src\components\WebDAWApp_WithTimeline.tsx" 2>nul
del /Q "frontend\src\components\WebDAWApp_WithMixer.tsx" 2>nul
del /Q "frontend\src\components\WebDAWApp_WithAnimation.tsx" 2>nul
del /Q "frontend\src\components\WebDAWApp_WithSeek.tsx" 2>nul

echo.
echo Test files deleted.
echo Now cleaning up App.tsx routes...
pause
