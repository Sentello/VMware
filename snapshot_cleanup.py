import os
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pyVim import connect
from pyVmomi import vim
import atexit
import ssl
import logging

# Configure logging to write to 'snapshot_cleanup.log'
logging.basicConfig(
    level=logging.INFO,
    filename='snapshot_cleanup.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from a .env file
load_dotenv()

def connect_to_vcenter(host, user, password):
    """
    Connects to a vCenter server without SSL certificate verification.

    Args:
        host (str): The vCenter server hostname or IP.
        user (str): The username for authentication.
        password (str): The password for authentication.

    Returns:
        ServiceInstance or None: The service instance if successful, None otherwise.
    """
    if not all([host, user, password]):
        logging.warning(f"Missing credentials for {host}. Skipping.")
        return None
    try:
        # Create an SSL context that skips certificate verification
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ssl_context.verify_mode = ssl.CERT_NONE  # Not recommended for production

        si = connect.SmartConnect(host=host, user=user, pwd=password, sslContext=ssl_context)
        atexit.register(connect.Disconnect, si)
        logging.info(f"Successfully connected to vCenter: {host}")
        return si
    except Exception as e:
        logging.error(f"Error connecting to vCenter {host}: {e}")
        return None

def get_all_vms(content):
    """
    Retrieves all virtual machines from a vCenter server.

    Args:
        content: The vCenter content object.

    Returns:
        list: A list of virtual machine objects.
    """
    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    return vm_view.view

def display_vm_snapshots(vms, vcenter_host):
    """
    Displays a list of virtual machines and their snapshots.

    Args:
        vms (list): List of virtual machine objects.
        vcenter_host (str): The vCenter hostname or IP.
    """
    logging.info(f"vCenter: {vcenter_host}")
    for vm in vms:
        logging.info(f"  VM: {vm.name}")
        if vm.snapshot:
            for snapshot in vm.snapshot.rootSnapshotList:
                logging.info(f"    - Snapshot Name: {snapshot.name}")
                logging.info(f"    - Creation Date: {snapshot.createTime.strftime('%Y-%m-%d %H:%M:%S')}")
                if snapshot.childSnapshotList:
                    print_child_snapshots(snapshot.childSnapshotList, "        ")
        else:
            logging.info("    - No snapshots found.")
        logging.info("-" * 20)

def print_child_snapshots(child_snapshots, indent):
    """
    Recursively prints child snapshots with indentation.

    Args:
        child_snapshots (list): List of child snapshot objects.
        indent (str): Indentation string for formatting.
    """
    for snapshot in child_snapshots:
        logging.info(f"{indent}- Snapshot Name: {snapshot.name}")
        logging.info(f"{indent}- Creation Date: {snapshot.createTime.strftime('%Y-%m-%d %H:%M:%S')}")
        if snapshot.childSnapshotList:
            print_child_snapshots(snapshot.childSnapshotList, indent + "    ")

def get_snapshot_age_input():
    """
    Prompts the user for the snapshot age in days, allowing 'q' to quit.

    Returns:
        int: The age in days entered by the user or default (30).
    """
    while True:
        age_days_str = input("Enter the age (in days) of snapshots to remove (default: 30, 'q' to quit): ")
        if age_days_str.lower() == 'q':
            sys.exit(0)
        if not age_days_str:
            return 30
        try:
            age_days = int(age_days_str)
            if age_days <= 0:
                print("Please enter a positive number.")
            else:
                return age_days
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")

def wait_for_task(task, initial_sleep=1, max_sleep=10):
    """
    Waits for a vCenter task to complete with exponential backoff.

    Args:
        task: The vCenter task object to monitor.
        initial_sleep (int): Initial sleep time in seconds.
        max_sleep (int): Maximum sleep time in seconds.

    Raises:
        Exception: If the task fails.
    """
    sleep_time = initial_sleep
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        time.sleep(sleep_time)
        sleep_time = min(sleep_time * 2, max_sleep)
    if task.info.state == vim.TaskInfo.State.error:
        raise Exception(f"Task error: {task.info.error}")

def delete_old_snapshots(vms, age_days):
    """
    Deletes snapshots older than the specified age, preserving newer children.

    Args:
        vms (list): List of virtual machine objects.
        age_days (int): Age threshold in days for snapshot deletion.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=age_days)
    for vm in vms:
        if vm.snapshot:
            for snapshot_tree in vm.snapshot.rootSnapshotList:
                delete_snapshot_if_old(snapshot_tree, cutoff_date, vm.name)

def delete_snapshot_if_old(snapshot_tree, cutoff_date, vm_name):
    """
    Recursively deletes old snapshots, keeping newer ones.

    Args:
        snapshot_tree: The snapshot tree object to process.
        cutoff_date (datetime): The cutoff date for deletion.
        vm_name (str): The name of the virtual machine.
    """
    # Process child snapshots first
    for child in snapshot_tree.childSnapshotList:
        delete_snapshot_if_old(child, cutoff_date, vm_name)
    # Check if this snapshot is older than the cutoff date
    if snapshot_tree.createTime < cutoff_date:
        logging.info(f"Attempting to delete snapshot '{snapshot_tree.name}' from VM '{vm_name}'...")
        try:
            task = snapshot_tree.snapshot.RemoveSnapshot_Task(removeChildren=False)
            wait_for_task(task)
            logging.info(f"Successfully deleted snapshot '{snapshot_tree.name}'.")
        except Exception as e:
            logging.error(f"Error deleting snapshot '{snapshot_tree.name}': {str(e)}")

def main():
    """Main function to run the snapshot management application."""
    parser = argparse.ArgumentParser(description="Manage vCenter snapshots.")
    parser.add_argument("-a", "--age", type=int, help="Age of snapshots to delete (in days).")
    args = parser.parse_args()

    # Connect to all configured vCenters
    vcenter_connections = {}
    vcenter_count = 1
    while True:
        host = os.getenv(f"VCENTER{vcenter_count}_HOST")
        if not host:
            break  # No more vCenter hosts defined
        user = os.getenv(f"VCENTER{vcenter_count}_USER")
        password = os.getenv(f"VCENTER{vcenter_count}_PASSWORD")

        if not all([host, user, password]):
            logging.warning(f"Incomplete vCenter{vcenter_count} credentials. Skipping.")
            vcenter_count += 1
            continue

        si = connect_to_vcenter(host, user, password)
        if si:
            vcenter_connections[host] = si
        vcenter_count += 1

    if not vcenter_connections:
        logging.error("No vCenter connections established. Exiting.")
        sys.exit(1)

    # Display snapshots for each vCenter
    for host, si in vcenter_connections.items():
        try:
            content = si.content
            vms = get_all_vms(content)
            display_vm_snapshots(vms, host)
        except Exception as e:
            logging.error(f"Error retrieving VMs from {host}: {e}")

    # Get user confirmation before proceeding with deletion
    proceed = input("Proceed with deleting old snapshots? (y/n): ").strip().lower()
    if proceed != 'y':
        logging.info("Deletion aborted by user.")
        sys.exit(0)

    # Determine the snapshot age to delete
    if args.age:
        age_days = args.age
    else:
        age_days = get_snapshot_age_input()

    # Delete old snapshots from each vCenter
    for host, si in vcenter_connections.items():
        try:
            content = si.content
            vms = get_all_vms(content)
            delete_old_snapshots(vms, age_days)
        except Exception as e:
            logging.error(f"Error during deletion on {host}: {e}")
        finally:
            logging.info(f"Disconnected from {host}")

    logging.info("Snapshot cleanup completed.")

if __name__ == "__main__":
    main()