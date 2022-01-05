# This will remove all snapshots for VMs that have them. The snapshots will be removed from each VM one by one. The command is as follows:
powershell
Get-VM | Get-Snapshot | Remove-Snapshot -confirm:$false

# To remove all snapshots from all VMs older than Feb 1, 2017:
powershell
Get-VM | Get-Snapshot | Where-Object {$_.Created -lt (Get-Date 1/Feb/2019)} | Remove-Snapshot -Confirm:$false
