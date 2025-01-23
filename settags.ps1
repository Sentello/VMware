# Get all VMs
$vms = Get-VM

foreach ($vm in $vms) {
    # Skip VMs with names starting with "vCLS-"
    if ($vm.Name -like "vCLS-*") {
        Write-Output "Skipping vCLS VM: $($vm.Name)"
        continue
    }

    $tags = Get-TagAssignment -Entity $vm

    if ($tags.Count -eq 0) {
        # Assign the 'Bronze' tag to the VM
        New-TagAssignment -Entity $vm -Tag "Bronze"
        Write-Output "Assigned tag 'Bronze' to VM: $($vm.Name)"
    }
}
