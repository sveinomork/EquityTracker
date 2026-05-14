$funds = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/funds"
$results = New-Object System.Collections.Generic.List[PSCustomObject]
foreach ($fund in $funds) {
    try {
        $dec = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/funds/$($fund.id)/summary?as_of_date=2025-12-31"
        $jan = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/funds/$($fund.id)/summary?as_of_date=2026-01-31"
        $results.Add([PSCustomObject]@{
            name = $fund.name
            delta_current_value = $jan.current_value - $dec.current_value
            delta_borrowed = $jan.capital_split.total_borrowed - $dec.capital_split.total_borrowed
            delta_interest = $jan.total_interest_paid - $dec.total_interest_paid
            delta_net_equity = $jan.net_equity_value - $dec.net_equity_value
            abs_impact = [Math]::Abs($jan.net_equity_value - $dec.net_equity_value)
        })
    } catch { }
}
$results | Sort-Object abs_impact -Descending | Select-Object name, delta_current_value, delta_borrowed, delta_interest, delta_net_equity | Format-Table -AutoSize
