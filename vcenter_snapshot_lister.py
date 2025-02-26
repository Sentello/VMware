import os
from dotenv import load_dotenv
from pyVim import connect
from pyVmomi import vim
import atexit
import ssl
from tabulate import tabulate
import logging

# Configure logging for better traceability
logging.basicConfig(level=logging.INFO)

# Load environment variables from the .env file
load_dotenv()

def connect_to_vcenter(host, user, password):
    """
    Connect to a vCenter server, skipping SSL certificate verification.

    Args:
        host (str): vCenter hostname or IP address.
        user (str): Username for authentication.
        password (str): Password for authentication.

    Returns:
        ServiceInstance or None: The service instance if connected, None if failed.
    """
    try:
        # Create an SSL context that skips certificate verification
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ssl_context.verify_mode = ssl.CERT_NONE  # Use with caution; not recommended for production
        si = connect.SmartConnect(host=host, user=user, pwd=password, sslContext=ssl_context)
        # Ensure disconnection when the script exits
        atexit.register(connect.Disconnect, si)
        logging.info(f"Connected to {host}")
        return si
    except Exception as e:
        logging.error(f"Failed to connect to {host}: {e}")
        return None

def get_all_vms(content):
    """
    Retrieve all virtual machines from a vCenter.

    Args:
        content: The vCenter content object.

    Returns:
        list: List of virtual machine objects.
    """
    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    return vm_view.view

def collect_snapshots(snapshot_tree, vm_name, vcenter_host, snapshots_list):
    """
    Recursively collect snapshot details from a snapshot tree.

    Args:
        snapshot_tree: The snapshot tree object.
        vm_name (str): Name of the virtual machine.
        vcenter_host (str): vCenter hostname or IP.
        snapshots_list (list): List to store snapshot data.
    """
    # Format the creation time as a readable string
    creation_time = snapshot_tree.createTime.strftime('%Y-%m-%d %H:%M:%S')
    snapshots_list.append({
        'vCenter': vcenter_host,
        'VM': vm_name,
        'Snapshot Name': snapshot_tree.name,
        'Creation Date': creation_time
    })
    # Recursively process child snapshots
    for child in snapshot_tree.childSnapshotList:
        collect_snapshots(child, vm_name, vcenter_host, snapshots_list)

def main():
    """
    Main function to connect to vCenters, collect snapshots, and display them in a table.
    """
    snapshots_data = []
    vcenter_count = 1

    # Loop through vCenter credentials in the .env file
    while True:
        host = os.getenv(f"VCENTER{vcenter_count}_HOST")
        if not host:
            break  # Exit loop if no more vCenters are found
        user = os.getenv(f"VCENTER{vcenter_count}_USER")
        password = os.getenv(f"VCENTER{vcenter_count}_PASSWORD")

        # Check if all required credentials are present
        if not all([host, user, password]):
            logging.warning(f"Incomplete credentials for VCENTER{vcenter_count}")
            vcenter_count += 1
            continue

        # Connect to the vCenter
        si = connect_to_vcenter(host, user, password)
        if si:
            content = si.content
            vms = get_all_vms(content)
            # Process each VM and its snapshots
            for vm in vms:
                if vm.snapshot:  # Check if the VM has snapshots
                    for root_snapshot in vm.snapshot.rootSnapshotList:
                        collect_snapshots(root_snapshot, vm.name, host, snapshots_data)
        vcenter_count += 1

    # Display the results
    if snapshots_data:
        # Sort by vCenter and VM name for readability
        snapshots_data.sort(key=lambda x: (x['vCenter'], x['VM']))
        # Prepare table data
        table = [[d['vCenter'], d['VM'], d['Snapshot Name'], d['Creation Date']] for d in snapshots_data]
        print(tabulate(table, headers=['vCenter', 'VM', 'Snapshot Name', 'Creation Date'], tablefmt='grid'))
    else:
        print("No snapshots found across all vCenters.")

if __name__ == "__main__":
    main()