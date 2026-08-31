param(
    [switch]$IncludeRestrictedReferences,
    [switch]$Refresh
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$RefRoot = Join-Path $Root "_references"
New-Item -ItemType Directory -Force -Path $RefRoot | Out-Null

function Clone-Or-Refresh {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Branch = ""
    )

    $Dest = Join-Path $RefRoot $Name
    if (Test-Path (Join-Path $Dest ".git")) {
        if ($Refresh) {
            Write-Host "[refresh] $Name"
            git -C $Dest fetch --depth 1 origin
            git -C $Dest reset --hard origin/HEAD
        } else {
            Write-Host "[skip] $Name already exists. Use -Refresh to update."
        }
        return
    }

    Write-Host "[clone] $Name"
    if ([string]::IsNullOrWhiteSpace($Branch)) {
        git clone --depth 1 --filter=blob:none $Url $Dest
    } else {
        git clone --depth 1 --filter=blob:none --branch $Branch $Url $Dest
    }
}

# Permissive / practical references
Clone-Or-Refresh "cytoscape.js" "https://github.com/cytoscape/cytoscape.js.git"
Clone-Or-Refresh "nhs-processmining" "https://github.com/nhsengland/ProcessMining.git"
Clone-Or-Refresh "bpmn-js-examples" "https://github.com/bpmn-io/bpmn-js-examples.git"

# Restricted/copyleft references are opt-in to reduce accidental copying into proprietary code.
if ($IncludeRestrictedReferences) {
    Write-Warning "GPL/AGPL/LGPL reference repositories are READ-ONLY references. Review OPEN_SOURCE_REFERENCE_GUIDE.md."
    Clone-Or-Refresh "pm4py" "https://github.com/process-intelligence-solutions/pm4py.git" "release"
    Clone-Or-Refresh "apromore-core" "https://github.com/apromore/ApromoreCore.git"
    Clone-Or-Refresh "cortado" "https://github.com/cortado-tool/cortado.git"
}

Write-Host ""
Write-Host "References ready under: $RefRoot"
Write-Host "Next: ask the AI agent to use templates/REFERENCE_ADOPTION_PROMPT.md"
