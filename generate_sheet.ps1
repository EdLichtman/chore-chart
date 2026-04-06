# Generate HTML checklist from chores.json

function Get-WeekAnchor {
    param([datetime]$Date = (Get-Date))
    $day = [int][DayOfWeek]::Sunday
    $current = [int]$Date.DayOfWeek
    $diff = if ($current -eq 0) { -6 } else { 1 - $current }
    $Date.AddDays($diff)
}

function Get-ISOWeek {
    param([datetime]$Date)
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $culture.Calendar.GetWeekOfYear($Date, [System.Globalization.CalendarWeekRule]::FirstFourDayWeek, [System.DayOfWeek]::Monday)
}

function Escape-Html {
    param([string]$Text)
    $Text -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;' -replace '"', '&quot;' -replace "'", '&#39;'
}

function Test-ChoreDueThisWeek {
    param($Chore, [datetime]$WeekStart)

    if ($Chore.lastAligned -eq 'pending' -or $null -eq $Chore.lastAligned) { return $true }

    try {
        $lastAligned = [datetime]::Parse($Chore.lastAligned)
    } catch {
        return $true
    }
    $n = $Chore.interval.n
    $unit = $Chore.interval.unit

    if ($unit -eq 'day') {
        return $Chore.interval.n -eq 1
    }

    $intervalDays = switch ($unit) {
        'week' { $n * 7 }
        'month' { $n * 30 }
        'year' { $n * 365 }
        default { 0 }
    }

    $dueDate = $lastAligned.AddDays($intervalDays)
    $weekEnd = $WeekStart.AddDays(6)

    # Check bi-weekly week pin
    if ($unit -eq 'week' -and $n -eq 2 -and $Chore.weekPin) {
        $currentISO = Get-ISOWeek $WeekStart
        $isOdd = $currentISO % 2 -eq 1
        if ($Chore.weekPin -eq 'odd' -and -not $isOdd) { return $false }
        if ($Chore.weekPin -eq 'even' -and $isOdd) { return $false }
    }

    return $dueDate -ge $WeekStart -and $dueDate -le $weekEnd
}

function New-Checklist {
    param([datetime]$Date = (Get-Date))

    $scriptPath = $PSScriptRoot
    $choreFile = Join-Path $scriptPath 'chores.json'
    $data = Get-Content $choreFile | ConvertFrom-Json
    $chores = $data.chores

    $weekStart = Get-WeekAnchor $Date
    $isoWeek = Get-ISOWeek $weekStart
    $weekStartStr = $weekStart.ToString('dddd, MMMM d, yyyy')
    $isOdd = $isoWeek % 2 -eq 1
    $oddEven = if ($isOdd) { 'odd' } else { 'even' }

    $dailyChores = $chores | Where-Object { $_.interval.unit -eq 'day' }
    $thisWeekChores = $chores | Where-Object { -not $_.weekend -and (Test-ChoreDueThisWeek $_ $weekStart) }
    $weekendChores = $chores | Where-Object { $_.weekend -and (Test-ChoreDueThisWeek $_ $weekStart) }

    $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chore Checklist</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f9f9f9;
            color: #333;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }
        h2 {
            background: #e8e8e8;
            padding: 10px;
            margin-top: 20px;
            border-left: 4px solid #333;
        }
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }
        .section {
            background: white;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .section h3 {
            margin-top: 0;
            color: #555;
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
        }
        ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        li {
            margin: 8px 0;
            line-height: 1.6;
        }
        input[type="checkbox"] {
            margin-right: 8px;
            cursor: pointer;
        }
        .sub-task {
            margin-left: 20px;
            color: #666;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border: 1px solid #ddd;
            margin: 10px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }
        th {
            background: #f0f0f0;
            font-weight: bold;
        }
        .overdue {
            color: #d32f2f;
            font-weight: bold;
        }
        .on-deck, .inactive {
            color: #666;
        }
        .day-fill {
            display: inline-block;
            border-bottom: 1px solid #333;
            width: 60px;
            text-align: center;
        }
        @media (max-width: 900px) {
            .container {
                grid-template-columns: 1fr;
            }
        }
        @media print {
            body { background: white; }
            .section { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <h1>Chore Checklist</h1>
    <p style="text-align: center; font-size: 16px;"><strong>Week of: $weekStartStr</strong> — ISO Week $isoWeek ($oddEven)</p>
"@

    # Daily chores table
    if ($dailyChores.Count -gt 0) {
        $html += "`n    <h2>Daily</h2>`n    <table>`n        <tr>`n            <th>Chore</th>`n"
        'S', 'M', 'T', 'W', 'T', 'F', 'S' | ForEach-Object { $html += "            <th>$_</th>`n" }
        $html += "        </tr>`n"

        foreach ($chore in $dailyChores) {
            $name = Escape-Html $chore.name
            $html += "        <tr>`n            <td style=`"text-align: left;`">$name</td>`n"
            1..7 | ForEach-Object { $html += "            <td><input type=`"checkbox`"></td>`n" }
            $html += "        </tr>`n"
        }
        $html += "    </table>`n"
    }

    # This Week & Weekend Chores
    if ($thisWeekChores.Count -gt 0 -or $weekendChores.Count -gt 0) {
        $html += "`n    <h2>This Week & Weekend Chores</h2>`n    <div class=`"container`">`n"

        # This Week section
        $html += "        <div class=`"section`">`n            <h3>This Week</h3>`n            <ul>`n"
        foreach ($chore in $thisWeekChores) {
            $name = Escape-Html $chore.name
            $html += "                <li><input type=`"checkbox`"> $name</li>`n"

            foreach ($note in $chore.notes) {
                $noteHtml = Escape-Html $note
                $html += "                    <ul class=`"sub-task`"><li>$noteHtml</li></ul>`n"
            }

            foreach ($req in $chore.requirements) {
                $reqName = Escape-Html $req.name
                $html += "                    <ul class=`"sub-task`"><li><input type=`"checkbox`"> $reqName</li></ul>`n"
            }
        }
        $html += "            </ul>`n        </div>`n`n"

        # Weekend Chores section
        $html += "        <div class=`"section`">`n            <h3>Weekend Chores</h3>`n            <ul>`n"
        foreach ($chore in $weekendChores) {
            $name = Escape-Html $chore.name
            $html += "                <li><input type=`"checkbox`"> $name</li>`n"

            foreach ($note in $chore.notes) {
                $noteHtml = Escape-Html $note
                $html += "                    <ul class=`"sub-task`"><li>$noteHtml</li></ul>`n"
            }

            foreach ($req in $chore.requirements) {
                $reqName = Escape-Html $req.name
                $html += "                    <ul class=`"sub-task`"><li><input type=`"checkbox`"> $reqName</li></ul>`n"
            }
        }
        $html += "            </ul>`n        </div>`n    </div>`n"
    }

    # On Deck & Inactive
    $html += @"

    <h2>On Deck</h2>
    <ul class="on-deck">
        <li>Mop First Floor (April 12)</li>
        <li>Vacuum Downstairs (April 12)</li>
        <li>Clean Little Trashes Around House (April 15)</li>
    </ul>

    <h2>Inactive</h2>
    <ul class="inactive">
        <li>Mow (resumes May 1)</li>
    </ul>

</body>
</html>
"@

    return $html
}

# Main execution
$html = New-Checklist
$outFile = Join-Path $PSScriptRoot 'checklist.html'
$html | Set-Content -Path $outFile -Encoding UTF8
Write-Host "Generated $outFile"
