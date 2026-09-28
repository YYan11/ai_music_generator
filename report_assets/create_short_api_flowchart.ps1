Add-Type -AssemblyName System.Drawing

$width = 1050
$height = 1500
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::White)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$pen = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 3)
$font = New-Object System.Drawing.Font("Arial", 22)
$brush = [System.Drawing.Brushes]::Black

function Draw-Box([int]$y, [string]$text, [bool]$rounded) {
    $rect = New-Object System.Drawing.Rectangle(175, $y, 700, 100)
    if ($rounded) { $graphics.DrawEllipse($pen, $rect) }
    else { $graphics.DrawRectangle($pen, $rect) }
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $graphics.DrawString($text, $font, $brush, [System.Drawing.RectangleF]$rect, $format)
}

function Draw-Arrow([int]$y1, [int]$y2) {
    $x = 525
    $graphics.DrawLine($pen, $x, $y1, $x, $y2 - 15)
    $points = [System.Drawing.Point[]]@([System.Drawing.Point]::new($x, $y2), [System.Drawing.Point]::new($x - 11, $y2 - 19), [System.Drawing.Point]::new($x + 11, $y2 - 19))
    $graphics.FillPolygon($brush, $points)
}

Draw-Box 50 "Start" $true
Draw-Box 210 "Enter Prompt" $false
Draw-Box 370 "Frontend" $false
Draw-Box 530 "POST /api/generate" $false
Draw-Box 690 "Detect Emotion" $false
Draw-Box 850 "Map Conditions" $false
Draw-Box 1010 "Generate MIDI" $false
Draw-Box 1170 "Return Result" $false
Draw-Box 1330 "Play / Download" $true

$pairs = @(@(150,210), @(310,370), @(470,530), @(630,690), @(790,850), @(950,1010), @(1110,1170), @(1270,1330))
foreach ($pair in $pairs) { Draw-Arrow $pair[0] $pair[1] }

$output = Join-Path $PSScriptRoot "music_generation_api_flowchart.png"
$bitmap.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bitmap.Dispose(); $font.Dispose(); $pen.Dispose()
Write-Output $output
