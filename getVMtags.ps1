# Get all VMs
$vms = Get-VM

foreach ($vm in $vms) {
    $tags = Get-TagAssignment -Entity $vm

    if ($tags.Count -eq 0) {
        Write-Output "VM without tags: $($vm.Name)"
    }
}
