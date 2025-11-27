@echo off
echo Updating Professional Tier page...

REM Backup old version
copy f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117\src\pages\ProfessionalTier.js f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117\src\pages\ProfessionalTier_OLD.js

REM Replace with new version
copy f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117\src\pages\ProfessionalTier_NEW.js f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117\src\pages\ProfessionalTier.js

echo Done! The page will auto-reload.
pause
