# Test file upload to DrumTracKAI backend
$url = "http://localhost:8000/api/upload"

# Create a small test audio file (simple WAV header)
$testFile = "test.wav"
$bytes = @(
    0x52, 0x49, 0x46, 0x46,  # "RIFF"
    0x24, 0x00, 0x00, 0x00,  # File size - 8
    0x57, 0x41, 0x56, 0x45,  # "WAVE"
    0x66, 0x6D, 0x74, 0x20,  # "fmt "
    0x10, 0x00, 0x00, 0x00,  # Chunk size
    0x01, 0x00,              # Audio format (PCM)
    0x01, 0x00,              # Num channels
    0x44, 0xAC, 0x00, 0x00,  # Sample rate (44100)
    0x88, 0x58, 0x01, 0x00,  # Byte rate
    0x02, 0x00,              # Block align
    0x10, 0x00,              # Bits per sample
    0x64, 0x61, 0x74, 0x61,  # "data"
    0x00, 0x00, 0x00, 0x00   # Data size
)
[IO.File]::WriteAllBytes($testFile, $bytes)

Write-Host "Testing upload to $url"
try {
    $response = Invoke-WebRequest -Uri $url -Method Post -InFile $testFile -ContentType "multipart/form-data" -Headers @{"Content-Disposition"="form-data; name=file; filename=test.wav"}
    Write-Host "Success: $($response.StatusCode)"
    Write-Host $response.Content
} catch {
    Write-Host "Error: $_"
    Write-Host $_.Exception.Response.StatusCode
}

Remove-Item $testFile -ErrorAction SilentlyContinue
