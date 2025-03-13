# Get all powered-on VMs
$vms = Get-VM | Where-Object { $_.PowerState -eq "PoweredOn" }

# Calculate total provisioned space (sum of all disk capacities)
$totalProvisioned = ($vms | Get-HardDisk | Measure-Object -Property CapacityGB -Sum).Sum

# Calculate total consumed space (sum of VM UsedSpaceGB)
$totalUsed = ($vms | Measure-Object -Property UsedSpaceGB -Sum).Sum

# Calculate savings
$savings = $totalProvisioned - $totalUsed

# Output results (rounded to the nearest GB)
Write-Host "Total Provisioned Space: $([math]::Round($totalProvisioned)) GB"
Write-Host "Total Consumed Space: $([math]::Round($totalUsed)) GB"
Write-Host "Estimated Savings: $([math]::Round($savings)) GB"
