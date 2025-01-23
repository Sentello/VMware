# Get all VMs
$vms = Get-VM
#script that retrieves all VMs and only prints the names of VMs without any tags

foreach ($vm in $vms) {
    $tags = Get-TagAssignment -Entity $vm

    if ($tags.Count -eq 0) {
        Write-Output "VM without tags: $($vm.Name)"
    }
}
