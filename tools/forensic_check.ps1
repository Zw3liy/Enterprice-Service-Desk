Write-Host "============================================================"
Write-Host "ENTERPRISE SERVICE DESK FORENSIC INVENTORY"
Write-Host "READ ONLY - NO MODIFICATIONS"
Write-Host "============================================================"
Write-Host ""
Write-Host "1. CURRENT GIT STATE"
Write-Host "------------------------------------------------------------"
git status
git branch --show-current
git log --oneline -10
Write-Host ""
Write-Host "2. REPOSITORY STRUCTURE"
Write-Host "------------------------------------------------------------"
Get-ChildItem -Directory | Select-Object Name
Write-Host ""
Write-Host "3. DJANGO PROJECT FILES"
Write-Host "------------------------------------------------------------"
Get-ChildItem -Recurse -Include "settings.py","urls.py","models.py","views.py","admin.py","forms.py" | Select-Object FullName
Write-Host ""
Write-Host "4. MIGRATION INVENTORY"
Write-Host "------------------------------------------------------------"
Get-ChildItem -Recurse -Directory -Filter migrations | ForEach-Object {
    Write-Host ""
    Write-Host $_.FullName
    Get-ChildItem $_.FullName -Filter "*.py" | Select-Object Name
}
Write-Host ""
Write-Host "5. TEMPLATE INVENTORY"
Write-Host "------------------------------------------------------------"
Get-ChildItem -Recurse -Include "*.html" | Select-Object FullName
Write-Host ""
Write-Host "6. STATIC FILE INVENTORY"
Write-Host "------------------------------------------------------------"
Get-ChildItem -Recurse -Path static -ErrorAction SilentlyContinue | Select-Object FullName
Write-Host ""
Write-Host "7. DJANGO ENVIRONMENT"
Write-Host "------------------------------------------------------------"
python --version
python -m django --version
Write-Host ""
Write-Host "8. DJANGO CHECK"
Write-Host "------------------------------------------------------------"
python manage.py check
Write-Host ""
Write-Host "============================================================"
Write-Host "FORENSIC CHECK COMPLETE"
Write-Host "NO FILES MODIFIED"
Write-Host "============================================================"
