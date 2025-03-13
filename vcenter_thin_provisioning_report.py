import os
from dotenv import load_dotenv
from pyVim import connect
from pyVmomi import vim
import atexit
import ssl
from tabulate import tabulate
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def connect_to_vcenter(host, user, password):
    """
    Connect to a vCenter server using provided credentials.
    
    Args:
        host (str): vCenter hostname or IP
        user (str): Username
        password (str): Password
    
    Returns:
        ServiceInstance or None if connection fails
    """
    try:
        # Create SSL context with verification disabled
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        si = connect.SmartConnect(
            host=host,
            user=user,
            pwd=password,
            sslContext=ssl_context
        )
        atexit.register(connect.Disconnect, si)
        logging.info(f"Connected to {host}")
        return si
    except Exception as e:
        logging.error(f"Failed to connect to {host}: {e}")
        return None

def get_all_vms(content):
    """Retrieve all VMs from vCenter."""
    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    return vm_view.view

def get_powered_on_vms(vms):
    """Filter VMs to only include powered-on VMs."""
    return [vm for vm in vms if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn]

def get_disk_info(vm):
    """
    Calculate provisioned and used disk space for a VM.
    
    Args:
        vm: VirtualMachine object
    
    Returns:
        dict: Provisioned and used space in bytes
    """
    # Calculate total provisioned space from disk capacities
    provisioned = 0
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualDisk):
            provisioned += device.capacityInBytes
    
    # Calculate total used space from disk extent file sizes
    used = 0
    try:
        for file in vm.layoutEx.file:
            if file.type == 'diskExtent':
                used += file.size
    except AttributeError as e:
        logging.error(f"Error accessing layoutEx for VM {vm.name}: {e}")
        # Fallback: assume used equals provisioned if layoutEx is unavailable
        used = provisioned
    
    return {'provisioned': provisioned, 'used': used}

def calculate_savings(provisioned, used):
    """Calculate space saved by thin provisioning."""
    return max(provisioned - used, 0)  # Prevent negative values

def display_data(data):
    """Display results in a formatted table."""
    # Convert bytes to GB
    for item in data:
        item['provisioned'] = round(item['provisioned'] / (1024**3), 2)
        item['used'] = round(item['used'] / (1024**3), 2)
        item['savings'] = round(item['savings'] / (1024**3), 2)
    
    table = [
        [d['vcenter'], d['vm_name'], d['provisioned'], d['used'], d['savings']]
        for d in data
    ]
    print(tabulate(table, headers=['vCenter', 'VM Name', 'Provisioned (GB)', 'Used (GB)', 'Saved (GB)'], tablefmt='grid'))

def main():
    data = []
    vcenter_count = 1

    # Connect to each vCenter specified in environment variables
    while True:
        host = os.getenv(f"VCENTER{vcenter_count}_HOST")
        if not host:
            break
        user = os.getenv(f"VCENTER{vcenter_count}_USER")
        password = os.getenv(f"VCENTER{vcenter_count}_PASSWORD")

        if not all([host, user, password]):
            logging.warning(f"Incomplete credentials for VCENTER{vcenter_count}. Skipping.")
            vcenter_count += 1
            continue

        si = connect_to_vcenter(host, user, password)
        if si:
            content = si.content
            all_vms = get_all_vms(content)
            powered_on_vms = get_powered_on_vms(all_vms)

            for vm in powered_on_vms:
                try:
                    disk_info = get_disk_info(vm)
                    savings = calculate_savings(disk_info['provisioned'], disk_info['used'])
                    data.append({
                        'vcenter': host,
                        'vm_name': vm.name,
                        'provisioned': disk_info['provisioned'],
                        'used': disk_info['used'],
                        'savings': savings
                    })
                except Exception as e:
                    logging.error(f"Error processing VM {vm.name}: {e}")
            connect.Disconnect(si)
        vcenter_count += 1

    if data:
        display_data(data)
    else:
        print("No powered-on VMs found.")

if __name__ == "__main__":
    main()