param([int]$Revision=3)
$ErrorActionPreference='Stop'
$version='v{0:d2}' -f $Revision
$clips=[ordered]@{SitUp_Cargo=63;Cargo_Sit_Idle=120;Cargo_Knock=84}
$reportPath=Join-Path $PSScriptRoot ('preview_media_'+$version+'.json')
if (Test-Path -LiteralPath $reportPath) { throw 'Refusing media report overwrite' }
$report=[ordered]@{fps=30;revision=$version;clips=[ordered]@{}}
foreach ($name in $clips.Keys) {
    $stem=$name+'_'+$version
    $folder=Join-Path $PSScriptRoot ('Previews\'+$stem+'\'+$name)
    $frames=Join-Path $folder 'motion_frames'
    $count=@(Get-ChildItem -LiteralPath $frames -Filter 'f*.png').Count
    if ($count -ne $clips[$name]) { throw "Expected $($clips[$name]) frames for $stem, got $count" }
    $target=Join-Path $folder ($stem+'.mp4')
    if (Test-Path -LiteralPath $target) { throw 'Refusing movie overwrite' }
    & ffmpeg -hide_banner -loglevel error -n -framerate 30 -i (Join-Path $frames 'f%04d.png') -c:v libx264 -pix_fmt yuv420p -movflags +faststart $target
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg failed' }
    $probe=& ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames,duration -of json $target
    if ($LASTEXITCODE -ne 0) { throw 'FFprobe failed' }
    $stream=($probe | ConvertFrom-Json).streams[0]
    if ($stream.r_frame_rate -ne '30/1' -or [int]$stream.nb_frames -ne $clips[$name]) { throw 'Incorrect encoded playback timing' }
    $report.clips[$stem]=$stream
    Write-Output "ENCODED $stem $($stream.duration)s $($stream.nb_frames) frames"
}
$json=$report | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($reportPath,$json,[Text.UTF8Encoding]::new($false))
