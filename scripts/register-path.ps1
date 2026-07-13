$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$newDir = "D:\Daksh\Business\Archangel\.venv\Scripts"
if ($currentPath -notlike "*$newDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$newDir", "User")
    Write-Output "PATH updated successfully — $newDir added to User PATH"
} else {
    Write-Output "PATH already contains $newDir — no change needed"
}
