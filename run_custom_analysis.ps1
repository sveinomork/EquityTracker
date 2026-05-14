$funds = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/funds"
$results = New-Object System.Collections.Generic.List[PSCustomObject]
foreach ($fund in $funds) {
    try {
        $dec = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/funds/$($fund.id)/summary?as_of_date=2025-12-31"
        $jan = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/funds/$($fund.id)/summary?as_of_date=2026-01-31"
        
        $dec_borrowed = $dec.current_value - $dec.net_equity_value
        $jan_borrowed = $jan.current_value - $jan.net_equity_value
        
        $results.Add([PSCustomObject]@{
            Fund = $fund.name
            Delta_Val = $jan.current_value - $dec.current_value
            Delta_Bor = $jan_borrowed - $dec_borrowed
            Delta_Int = $jan.total_interest_paid - $dec.total_interest_paid
            Delta_Eq  = $jan.net_equity_value - $dec.net_equity_value
            Abs_Bor   = [Math]::Abs($jan_borrowed - $dec_borrowed)
            Abs_Eq    = [Math]::Abs($jan.net_equity_value - $dec.net_equity_value)
        })
    } catch { }
}
$results | Sort-Object Abs_Bor, Abs_Eq -Descending | Select-Object Fund, Delta_Val, Delta_Bor, Delta_Int, Delta_Eq | Format-Table -AutoSize
