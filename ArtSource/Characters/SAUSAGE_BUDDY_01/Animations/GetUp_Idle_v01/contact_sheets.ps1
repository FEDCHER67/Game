param([Parameter(Mandatory=$true)][string]$ReviewRoot)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$root=[IO.Path]::GetFullPath($ReviewRoot)
if (-not $root.StartsWith($PSScriptRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Outputs must stay in the getup package' }
$font=New-Object System.Drawing.Font('Segoe UI',13)
$small=New-Object System.Drawing.Font('Segoe UI',11)
$brush=[Drawing.Brushes]::White
$revisionSuffix=''
if ($root -match '_(v\d{2})$') { $revisionSuffix='_'+$Matches[1] }
Get-ChildItem -LiteralPath $root -Directory | ForEach-Object {
    $clip=$_
    $views=@('side','three_quarter')
    $files=@()
    foreach ($view in $views) { $files += @(Get-ChildItem -LiteralPath (Join-Path $clip.FullName $view) -Filter '*.png' | Sort-Object Name) }
    if ($files.Count -ne 20) { throw "Expected 20 panels for $($clip.Name), got $($files.Count)" }
    $stem=$clip.Name+$revisionSuffix
    $path=Join-Path $clip.FullName ($stem+'_contact_sheet.png')
    if (Test-Path -LiteralPath $path) { throw "Refusing overwrite: $path" }
    $canvas=New-Object Drawing.Bitmap(1800,1610)
    $graphics=[Drawing.Graphics]::FromImage($canvas)
    $graphics.Clear([Drawing.Color]::FromArgb(35,39,46))
    $graphics.DrawString($stem+' | 30 fps | side (top), three-quarter (bottom)', $font,$brush,15,10)
    for ($i=0; $i -lt $files.Count; $i++) {
        $x=($i % 5)*360; $y=45+[int][Math]::Floor($i/5)*390
        $pic=[Drawing.Image]::FromFile($files[$i].FullName)
        $graphics.DrawImage($pic,$x,$y,360,360)
        $graphics.DrawString(($files[$i].BaseName -replace '^.*_v\d\d_\d\d_',''),$small,$brush,$x+8,$y+364)
        $pic.Dispose()
    }
    $canvas.Save($path,[Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose();$canvas.Dispose()
    Write-Output $path
}
$font.Dispose();$small.Dispose()
