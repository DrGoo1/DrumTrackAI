if (Test-Path "LandingPage.html") { Rename-Item "LandingPage.html" "LandingPage.html.OLD" }
if (Test-Path "landing_page.html") { Rename-Item "landing_page.html" "landing_page.html.OLD" }
if (Test-Path "LandingPage.js") { Rename-Item "LandingPage.js" "LandingPage.js.OLD" }
if (Test-Path "landing_page.js") { Rename-Item "landing_page.js" "landing_page.js.OLD" }
Write-Host "Done! Old files renamed."
