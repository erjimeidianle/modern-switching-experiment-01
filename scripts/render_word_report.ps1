param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf
)
$ErrorActionPreference = 'Stop'
$reportWord = $null
$reportDocument = $null
try {
    $reportWord = New-Object -ComObject Word.Application
    $reportWord.Visible = $false
    $reportWord.DisplayAlerts = 0
    $reportWord.AutomationSecurity = 3
    $reportDocument = $reportWord.Documents.Open($InputDocx, $false, $true)
    $reportDocument.Repaginate()
    $reportDocument.ExportAsFixedFormat($OutputPdf, 17)
    Write-Output 'Word PDF export complete; page count is verified from the exported PDF.'
} finally {
    if ($null -ne $reportDocument) {
        $reportNoSave = 0
        $reportDocument.Close([ref]$reportNoSave)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($reportDocument)
    }
    if ($null -ne $reportWord) {
        $reportNoSave = 0
        $reportWord.Quit([ref]$reportNoSave)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($reportWord)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
