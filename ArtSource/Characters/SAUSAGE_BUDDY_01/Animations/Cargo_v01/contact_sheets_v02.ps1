param([Parameter(Mandatory=$true)][string]$ReviewRoot,[string]$Clip="")
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$root=[IO.Path]::GetFullPath($ReviewRoot)
$allowed=[IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar
if (-not $root.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)) { throw 'Outputs must stay in Cargo_v01' }
$font=New-Object System.Drawing.Font('Segoe UI',13)
$small=New-Object System.Drawing.Font('Segoe UI',11)
$brush=[Drawing.Brushes]::White
$suffix=''
if ($root -match '_(v\d{2})$') { $suffix='_'+$Matches[1] }
Get-ChildItem -LiteralPath $root -Directory | Where-Object { $Clip -eq "" -or $_.Name -eq $Clip } | ForEach-Object {
    $clip=$_
    $files=@()
    foreach ($view in @('side','three_quarter')) {
        $files+=@(Get-ChildItem -LiteralPath (Join-Path $clip.FullName $view) -Filter '*.png' | Sort-Object Name)
    }
    if ($files.Count -ne 20) { throw "Expected 20 panels for $($clip.Name), got $($files.Count)" }
    $stem=$clip.Name+$suffix
    $path=Join-Path $clip.FullName ($stem+'_contact_sheet.png')
    if (Test-Path -LiteralPath $path) { throw "Refusing overwrite: $path" }
    $canvas=New-Object Drawing.Bitmap(1800,1610)
    $g=[Drawing.Graphics]::FromImage($canvas)
    $g.Clear([Drawing.Color]::FromArgb(35,39,46))
    $g.DrawString($stem+' | 30 fps | side (top), three-quarter (bottom)',$font,$brush,15,10)
    for ($i=0;$i -lt 20;$i++) {
        $x=($i % 5)*360;$y=45+[int][Math]::Floor($i/5)*390
        $pic=[Drawing.Image]::FromFile($files[$i].FullName)
        $g.DrawImage($pic,$x,$y,360,360)
        $g.DrawString(($files[$i].BaseName -replace '^.*_v\d\d_\d\d_',''),$small,$brush,$x+8,$y+364)
        $pic.Dispose()
    }
    $canvas.Save($path,[Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose();$canvas.Dispose();Write-Output $path
}
$font.Dispose();$small.Dispose()
