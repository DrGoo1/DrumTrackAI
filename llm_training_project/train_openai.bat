@echo off
REM OpenAI Fine-Tuning Script for DrumTracKAI Drummer LLM
REM ======================================================

echo ======================================================================
echo DrumTracKAI LLM Training - OpenAI Fine-Tuning
echo ======================================================================
echo.

REM Check for OpenAI API key
if "%OPENAI_API_KEY%"=="" (
    echo ERROR: OPENAI_API_KEY not set
    echo.
    echo Set your API key:
    echo   set OPENAI_API_KEY=sk-your-key-here
    echo.
    pause
    exit /b 1
)

REM Check if training data exists
if not exist "training_datasets\multitask_full.jsonl" (
    echo ERROR: Training data not found
    echo Expected: training_datasets\multitask_full.jsonl
    echo.
    echo Run: python combine_training_datasets.py
    echo.
    pause
    exit /b 1
)

echo Training Data: training_datasets\multitask_full.jsonl
for %%A in (training_datasets\multitask_full.jsonl) do echo Size: %%~zA bytes
echo.

REM Check if openai CLI is installed
where openai >nul 2>nul
if errorlevel 1 (
    echo OpenAI CLI not found. Installing...
    pip install openai
)

echo.
echo Starting OpenAI fine-tuning...
echo Model: gpt-4-turbo
echo Suffix: drumtrackai-drummer-v1
echo.
echo This will take 30-60 minutes for 91K examples.
echo.

REM Create fine-tune
openai api fine_tunes.create ^
  -t training_datasets\multitask_full.jsonl ^
  -m gpt-4-turbo ^
  --suffix drumtrackai-drummer-v1 ^
  --n_epochs 3

echo.
echo ======================================================================
echo Training started!
echo ======================================================================
echo.
echo Monitor progress:
echo   openai api fine_tunes.follow -i ^<fine-tune-id^>
echo.
echo Or check dashboard: https://platform.openai.com/finetune
echo.
pause
