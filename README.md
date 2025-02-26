# VMware vSphere Management Scripts

This repository contains a collection of scripts for managing VMware vSphere environments, including tasks such as:

*   Listing and managing VM snapshots.
*   Managing VM tags.
*   Fixing Platform Services Controller (PSC) replication issues.
*   Backing up ESXi configurations.

## Scripts Overview

### Python Scripts

These scripts use the `pyvmomi` library to interact with the vSphere API. They require Python 3 and the dependencies listed in `requirements.txt`. They are designed to connect to multiple vCenter servers, using credentials stored in a `.env` file.

*   **`snapshot_cleanup.py`**: Connects to one or more vCenter servers, retrieves all VMs, displays their snapshots, and deletes snapshots older than a specified age (default: 30 days).
    *   **Usage**:
        *   Set environment variables `VCENTER1_HOST`, `VCENTER1_USER`, `VCENTER1_PASSWORD`, `VCENTER2_HOST`, etc., with the credentials for each vCenter server.
        *   Run the script: `python snapshot_cleanup.py`
        *   Optionally, specify the age of snapshots to delete using the `-a` or `--age` argument: `python snapshot_cleanup.py -a 7` (deletes snapshots older than 7 days).
        *   The script will prompt for confirmation before deleting snapshots.
        *   Logs are written to `snapshot_cleanup.log`.
*   **`vcenter_snapshot_lister.py`**: Connects to one or more vCenter servers, retrieves all VMs, and lists their snapshots in a tabular format.
    *   **Usage**:
        *   Set environment variables `VCENTER1_HOST`, `VCENTER1_USER`, `VCENTER1_PASSWORD`, `VCENTER2_HOST`, etc., with the credentials for each vCenter server.
        *   Run the script: `python vcenter_snapshot_lister.py`
        *   The script will output a table with vCenter, VM name, snapshot name, and creation date.

### PowerShell Scripts

These scripts use PowerCLI to interact with the vSphere environment. They require a PowerCLI environment to be set up.

*   **`getVMtags.ps1`**: Retrieves all VMs and prints the names of VMs that don't have any tags assigned.
    *    **Usage**: Run in a PowerCLI environment: `.\getVMtags.ps1`
*   **`setVMtags.ps1`**: Assigns the tag "Bronze" to any VM that doesn't already have a tag, excluding VMs with names starting with "vCLS-".
    *   **Usage**: Run in a PowerCLI environment: `.\setVMtags.ps1`

### Shell Scripts

*   **`fixpsc.sh`**: This script is used to fix replication issues with Platform Services Controllers (PSCs) in a vSphere environment. It involves changing the domain state, decommissioning the broken PSC, rejoining the domain, and testing replication.
    * **Usage**:
        * This script must be run from the affected PSC.
        * **Prerequisites**:
            * Offline snapshots of VCs/PSCs.
            * SSO Admin Password.
            * FQDN of a healthy PSC.
            * Root password of the healthy PSC.
            * Bash shell enabled on the healthy PSC.
        * Run the script: `./fixpsc.sh`
        * The script will prompt for the healthy PSC FQDN and passwords.
        * A log file `fix_psc_state.log` will be created.

## Fixing Broken PSC Replication

This section provides detailed instructions on how to fix broken PSC replication, including steps, commands, and visual aids.

**References:**

*   [Resolving stale PSC entries from your vSphere environment](https://cloud-duo.com/2021/03/resolving-stale-psc-entries-from-your-vsphere-environment/)
*   [vCenter error 400 Failed to connect to VMware Lookup Service](https://cloud-duo.com/2021/04/vcenter-error-400-failed-to-connect-to-vmware-lookup-service/)

**Steps:**

1.  **Identify the Issue:** The following images illustrate the problem, showing a transition from a broken state to a fixed state:

    **Before (Broken):**

    ![image](https://user-images.githubusercontent.com/44606412/187523956-9069cc8a-ac33-43bf-ac6e-392d769b1aac.png)

    **After (Fixed):**

    ![image](https://user-images.githubusercontent.com/44606412/187520586-7a4c0056-194d-46f8-bf56-ce341086578e.png)

2.  **Create Replication Agreements:** Use the following command to create a new replication agreement between PSCs (replace `vc01`, `vc02`, `vc03`, `vc04`, and `Administrator` with your actual values):

    ```bash
    cd /usr/lib/vmware-vmdir/bin
    ./vdcrepadmin -f createagreement -2 -h vc01 -H vc02 -u Administrator
    ./vdcrepadmin -f createagreement -2 -h vc01 -H vc03 -u Administrator
    ./vdcrepadmin -f createagreement -2 -h vc01 -H vc04 -u Administrator
    ./vdcrepadmin -f createagreement -2 -h vc02 -H vc03 -u Administrator
    ./vdcrepadmin -f createagreement -2 -h vc02 -H vc04 -u Administrator
    ./vdcrepadmin -f createagreement -2 -h vc03 -H vc04 -u Administrator
    ```

3.  **Show All PSCs:** Run this command to show all PSCs in the vSphere domain (replace `PSC_FQDN` and `administrator` with your actual values):

    ```bash
    vdcrepadmin -f showservers -h PSC_FQDN -u administrator
    ```

4.  **Show Partners:** Use this command to display the partner PSC (replace `PSC_FQDN` and `administrator` with your actual values):

    ```bash
    vdcrepadmin -f showpartners -h PSC_FQDN -u administrator
    ```
    *   For more detailed instructions and troubleshooting, refer to the `fixpsc.sh` script and the linked articles.

## Setup and Dependencies

1.  **Python Environment:**
    *   Install Python 3.
    *   Create a virtual environment (recommended): `python3 -m venv venv`
    *   Activate the virtual environment:
        *   On Linux/macOS: `source venv/bin/activate`
        *   On Windows: `venv\Scripts\activate`
    *   Install the required Python packages: `pip install -r requirements.txt`
2.  **PowerCLI Environment:**
    *   Install PowerCLI.
    *   Connect to your vCenter server: `Connect-VIServer <vcenter_server>`
3. **Environment Variables:**
    * The python scripts use environment variables for vCenter credentials. Create a `.env` file in the project root directory and define the following variables:
    ```
    VCENTER1_HOST=your_vcenter_host
    VCENTER1_USER=your_vcenter_username
    VCENTER1_PASSWORD=your_vcenter_password
    VCENTER2_HOST=...
    ```
    * Replace `your_vcenter_host`, `your_vcenter_username`, and `your_vcenter_password` with your actual vCenter credentials. Add more `VCENTERn_...` variables for additional vCenter servers.

## Additional Notes

* The original README.md contained information about backing up ESXi. This information has been retained below.
* The python scripts disable SSL verification, which is not recommended for production.

## Backup ESXi

To backup ESXi, use the following steps:

1.  **Navigate to the backup directory:**

    ```bash
    cd /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/esxi_backup
    ```

2.  **Edit the `esxi_backup.sh` script:**

    ```bash
    vi esxi_backup.sh
    ```

    **Script Content:**

    ```bash
    #!/bin/sh
    vim-cmd hostsvc/firmware/sync_config
    vim-cmd hostsvc/firmware/backup_config
    find /scratch/downloads/ -name \*.tgz -exec cp {} /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/ESXi_config_backup_$(hostname)_$(date +’%Y%m%d_%H%M%S’).tgz \;
    find /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/ -type f -name '*.tgz' -mtime +20 -exec rm {} \;
    ```

3.  **Change permissions:**

    ```bash
    chmod +x esxi_backup.sh
    ```

4.  **Create Cron Job:** Edit `/var/spool/cron/crontabs/root` and add the following line (adjust the path to `esxi_backup.sh` if necessary):

    ```
    1    1    *   *   *   /vmfs/volumes/KCP-SDX1-AO-DATASTORE01/esxi_backup.sh
