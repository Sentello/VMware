# This will remove all snapshots for VMs that have them. The snapshots will be removed from each VM one by one:
```
powershell
Get-VM | Get-Snapshot | Remove-Snapshot -confirm:$false
```

# To remove all snapshots from all VMs older than Feb 1, 2017:
```
powershell
Get-VM | Get-Snapshot | Where-Object {$_.Created -lt (Get-Date 1/Feb/2019)} | Remove-Snapshot -Confirm:$false
```

# Backup ESXi with script:
```
cd /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/esxi_backup
```
**edit file:**  vi esxi_backup.sh

```
#!/bin/sh
vim-cmd hostsvc/firmware/sync_config
vim-cmd hostsvc/firmware/backup_config
find /scratch/downloads/ -name \*.tgz -exec cp {} /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/ESXi_config_backup_$(hostname)_$(date +’%Y%m%d_%H%M%S’).tgz \;
find /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/ -type f -name '*.tgz' -mtime +20 -exec rm {} \;
```

**change permissions:**  chmod +x esxi_backup.sh

**Create Cron Job:** vi /var/spool/cron/crontabs/root

```
1    1    *   *   *   /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/esxi_backup.sh
```
# FIX broken PSC replication:
From this:

![image](https://user-images.githubusercontent.com/44606412/187523956-9069cc8a-ac33-43bf-ac6e-392d769b1aac.png)


To this:

![image](https://user-images.githubusercontent.com/44606412/187520586-7a4c0056-194d-46f8-bf56-ce341086578e.png)

Use the following command to create a new replication agreement between PSCs:

```
cd /usr/lib/vmware-vmdir/bin
./vdcrepadmin -f createagreement -2 -h vc01 -H vc02 -u Administrator
./vdcrepadmin -f createagreement -2 -h vc01 -H vc03-u Administrator
./vdcrepadmin -f createagreement -2 -h vc01 -H vc04 -u Administrator
./vdcrepadmin -f createagreement -2 -h vc02 -H vc03 -u Administrator
./vdcrepadmin -f createagreement -2 -h vc02 -H vc04 -u Administrator
./vdcrepadmin -f createagreement -2 -h vc03 -H vc04 -u Administrator
```
Run this command to show all PSCs in the vSphere domain:
...
vdcrepadmin -f showservers -h PSC_FQDN -u administrator
...

VDCREPADMIN showpartners is to display the partner PSC:

...
vdcrepadmin -f showpartners -h PSC_FQDN -u administrator
...
