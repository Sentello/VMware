# Get all VMs
$vms = Get-VM

# Assign the 'Bronze' tag to the VM if there is no tag
foreach ($vm in $vms) {
    # Skip VMs with names starting with "vCLS-"
    if ($vm.Name -like "vCLS-*") {
        Write-Output "Skipping vCLS VM: $($vm.Name)"
        continue
    }

    $tags = Get-TagAssignment -Entity $vm

    if ($tags.Count -eq 0) {
        New-TagAssignment -Entity $vm -Tag "Bronze"
        Write-Output "Assigned tag 'Bronze' to VM: $($vm.Name)"
    }
}
