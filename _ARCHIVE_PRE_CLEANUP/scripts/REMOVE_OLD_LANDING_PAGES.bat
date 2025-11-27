@echo off
echo ========================================
echo Removing Old Static Landing Page Files
echo ========================================
echo.

echo Renaming old HTML files to .OLD...

if exist "LandingPage.html" (
    ren "LandingPage.html" "LandingPage.html.OLD"
    echo ✓ Renamed LandingPage.html
)

if exist "landing_page.html" (
    ren "landing_page.html" "landing_page.html.OLD"
    echo ✓ Renamed landing_page.html
)

if exist "LandingPage.js" (
    ren "LandingPage.js" "LandingPage.js.OLD"
    echo ✓ Renamed LandingPage.js
)

if exist "landing_page.js" (
    ren "landing_page.js" "landing_page.js.OLD"
    echo ✓ Renamed landing_page.js
)

echo.
echo ========================================
echo ✅ Done! Old files renamed.
echo ========================================
echo.
echo Now the React app will load directly
echo without showing the old page first!
echo.
pause
