#!/bin/bash
# Run this from the affected PSC 
# Luciano Delorenzi [ldelorenzi@vmware.com] - 12/20/2019

#########################################################
# NOTE: This works on external and embedded PSCs
# This script will do the following
# 1: Change domain state of broken PSC to 0
# 2: Decomission broken PSC from a healthy PSC on the environment
# 3: Re-join the domain using the data.mdb of a healthy PSC and therefore fix replication
# 4: Peform a quick replication test which involves creating a dummy user
#
# What is needed?
# 1: Offline snapshots of VCs/PSCs - IMPORTANT
# 2: SSO Admin Password
# 3: FQDN of healthy PSC
# 4: Root password of healthy PSC
# 5: Bash shell enabled on the healthy PSC




LOGFILE="fix_psc_state.log"

echo "==================================" | tee -a $LOGFILE

echo "NOTE: This works on external and embedded PSCs"
echo "This script will do the following"
echo "1: Change domain state of broken PSC to 0"
echo "2: Decomission broken PSC from a healthy PSC on the environment"
echo "3: Re-join the domain using the data.mdb of a healthy PSC and therefore fix replication"
echo "4: Peform a quick replication test which involves creating a dummy user"
echo
echo "What is needed?"
echo "1: Offline snapshots of VCs/PSCs"
echo "2: SSO Admin Password"
echo "3: FQDN of healthy PSC"
echo "4: Root password of healthy PSCs"
echo "5: Bash shell enabled on the healthy PSC"


echo "Fixing PSC state for $HOSTNAME started on $(date)" | tee -a $LOGFILE
echo ""| tee -a $LOGFILE
read -p "Please provide a healthy PSC FQDN: " HEALTHYPSC
echo ""
DN=$(/opt/likewise/bin/lwregshell list_values '[HKEY_THIS_MACHINE\Services\vmdir]' | grep dcAccountDN | awk '{$1=$2=$3="";print $0}'|tr -d '"'|sed -e 's/^[ \t]*//')
echo "Detected DN: $DN" | tee -a $LOGFILE 
PNID=$(/opt/likewise/bin/lwregshell list_values '[HKEY_THIS_MACHINE\Services\vmafd\Parameters]' | grep PNID | awk '{print $4}'|tr -d '"')
echo "Detected PNID: $PNID" | tee -a $LOGFILE
PSC=$(/opt/likewise/bin/lwregshell list_values '[HKEY_THIS_MACHINE\Services\vmafd\Parameters]' | grep DCName | awk '{print $4}'|tr -d '"')
echo "Detected PSC: $PSC" | tee -a $LOGFILE
DOMAIN=$(/opt/likewise/bin/lwregshell list_values '[HKEY_THIS_MACHINE\Services\vmafd\Parameters]' | grep DomainName | awk '{print $4}'|tr -d '"')
echo "Detected SSO domain name: $DOMAIN" | tee -a $LOGFILE
SITE=$(/opt/likewise/bin/lwregshell list_values '[HKEY_THIS_MACHINE\Services\vmafd\Parameters]' | grep SiteName | awk '{print $4}'|tr -d '"')
MACHINEID=$(cat /etc/vmware/install-defaults/sca.hostid)
echo "Detected Machine ID: $MACHINEID" | tee -a $LOGFILE

DOMAINCN="dc=$(echo "$DOMAIN" | sed 's/\./,dc=/g')"
ADMIN="cn=administrator,cn=users,$DOMAINCN"
USERNAME="administrator@${DOMAIN^^}"

echo ""
read -s -p "Enter password for administrator@$DOMAIN: " DOMAINPASSWORD
echo ""
read -s -p "Enter root password for $HEALTHYPSC: " HEALTHYPASSWORD
echo ""
#CHECK IF HEALTHY PSC HAS BASH SHELL ENABLED
HEALTHCHECKOUTPUT=$(sshpass -p "$HEALTHYPASSWORD" ssh -q -o StrictHostKeyChecking=no root@$HEALTHYPSC << EOF
echo "This is a bash shell test"
EOF
) 

echo "################################"
if  echo "$HEALTHCHECKOUTPUT" | grep "This is a bash shell test" 
then
	echo "Bash shell is enabled on the healthy node - Script will continue"
else
    echo "Bash shell is not enabled on the healthy node"
	echo "Please login to $HEALTHYPSC and run 'chsh -s /bin/bash' - then, re-run this script"
	exit 0
fi



#Set domain state to 0
/opt/likewise/bin/lwregshell set_value '[HKEY_THIS_MACHINE\Services\vmafd\Parameters]' "DomainState" 0
service-control --stop vmdird

#SSH to Healthy PSC and run command
echo "Leaving federation and restarting vmdird service..."

VDCLEAVEFEDOUTPUT=$(sshpass -p "$HEALTHYPASSWORD" ssh -q -o StrictHostKeyChecking=no root@$HEALTHYPSC << EOF
/usr/lib/vmware-vmdir/bin/vdcleavefed -h $PNID -u administrator -w "$DOMAINPASSWORD"
export VMWARE_CIS_HOME='/usr/lib'
export VMWARE_JAVA_HOME='/usr/java/jre-vmware'
export VMWARE_PYTHON_BIN='/usr/bin/python'
export VMWARE_TOMCAT='/var/opt/apache-tomcat'
export VMWARE_TOMCAT_8='/var/opt/apache-tomcat'
export VMWARE_OPENSSL_BIN='/usr/bin/openssl'
export VMWARE_VAPI_HOME='/usr/lib/vmware-vapi'
export LC_ALL='en_US.UTF-8'
export VMWARE_VAPI_PYTHONPATH='/usr/lib/vmware-vapi/lib/python:/usr/lib/vmware-vapi/lib/python/vapi_runtime-2.100.0-py2.py3-none-any.whl:/usr/lib/vmware-vapi/lib/python/vapi_common-2.100.0-py2.py3-none-any.whl:/usr/lib/vmware-vapi/lib/python/vapi_common_client-2.100.0-py2.py3-none-any.whl:/usr/lib/vmware-vapi/lib/python/vapi_clients-2.100.0-py2.py3-none-any.whl:/usr/lib/vmware-vapi/lib/python/Werkzeug-0.11.4-py2.py3-none-any.whl:/usr/lib/vmware-vapi/lib/python/prompt_toolkit-1.0.0-py2-none-any.whl:/usr/lib/vmware-vapi/lib/python/wcwidth-0.1.6-py2.py3-none-any.whl:/usr/lib/vmware-vapi/lib/python/Pygments-2.1.3-py2.py3-none-any.whl'
export VMWARE_JAVA_WRAPPER='/bin/heapsize_wrapper.sh'
export VMWARE_COMMON_JARS='/usr/lib/vmware/common-jars'
export VMWARE_VCHA_SMALLFILES_DIR='/etc/vmware/service-state'
export VMWARE_VCHA_LARGEFILES_DIR='/storage/service-state'
export VMWARE_VCHA_SQLITEFILES_DIR='/storage/sqlite-state'
export KRB5_CONFIG='/var/lib/likewise/krb5-affinity.conf:/etc/likewise/likewise-krb5-ad.conf:/etc/krb5.conf'
export VMWARE_BUILD_TYPE='release'
export VMWARE_INSTALL_PARAMETER='/bin/install-parameter'
export PYTHONIOENCODING='utf-8'
export VMWARE_RUN_FIRSTBOOTS='/bin/run-firstboot-scripts'
export VMWARE_CLOUDVM_RAM_SIZE='/usr/sbin/cloudvm-ram-size'
export VMWARE_LOG_DIR='/var/log'
export VMWARE_RUNTIME_DATA_DIR='/var'
export VMWARE_DATA_DIR='/storage'
export VMWARE_CFG_DIR='/etc/vmware'
export VMWARE_PYTHON_PATH='/usr/lib/vmware/site-packages'
export VMWARE_PYTHON_MODULES_HOME='/usr/lib/vmware/site-packages/cis'
export VMWARE_TMP_DIR='/var/tmp/vmware'
export VMWARE_VAPI_CFG_DIR='/etc/vmware/vmware-vapi'
sleep 180
service-control --stop vmdird && service-control --start vmdird
EOF
) 

if echo $VDCLEAVEFEDOUTPUT | grep 'vdcleavefd offline'
then
	echo "Succesfully executed vdcleavefed"
else
    echo "Vdcleavefed failed - Please check vmdird logs"
	exit 0
fi

find /storage/db/vmware-vmdir/ -name "*mdb*" -exec mv {} /tmp/ \;
service-control --start vmdird
echo ""
echo "#######################################"
/usr/lib/vmware-vmafd/bin/vdcpromo -u Administrator -w "$DOMAINPASSWORD" -s $SITE -h $PNID -H $HEALTHYPSC | tee -a $LOGFILE

/usr/lib/vmware-vmafd/bin/vmafd-cli set-machine-id --server-name $PNID --id $MACHINEID | tee -a $LOGFILE
service-control --stop --all && service-control --start --all
echo ""
echo "#######################################"
echo "Testing replication: " | tee -a $LOGFILE
echo "Creating user on this node"  | tee -a $LOGFILE
/usr/lib/vmware-vmafd/bin/dir-cli user create --account 'TestAccount' --user-password 'VMware123!VMware123!' --first-name 'FirstName' --last-name 'LastName' --login administrator@$DOMAIN --password "$DOMAINPASSWORD"
sleep 30
echo "Checking existence of user on healthy node..."  | tee -a $LOGFILE
TESTUSEROUTPUT=$(sshpass -p "$HEALTHYPASSWORD" ssh -q -o StrictHostKeyChecking=no root@$HEALTHYPSC << EOF
/bin/bash
/usr/lib/vmware-vmafd/bin/dir-cli user find-by-name --account 'TestAccount' --login administrator@$DOMAIN --password "$DOMAINPASSWORD"
EOF
) 

if echo "$TESTUSEROUTPUT" | grep TestAccount ;
then
	echo "Replication is successful!" | tee -a $LOGFILE
	echo "Please restart vmdird service on the remaining PSCs in the SSO domain using the following command: "
	echo "service-control --stop vmdird && service-control --start vmdird"
else
	echo "Replication is not successful - Please check vmdir logs" | tee -a $LOGFILE
fi

/usr/lib/vmware-vmafd/bin/dir-cli user delete --account 'TestAccount' --login administrator@$DOMAIN --password "$DOMAINPASSWORD"| tee -a $LOGFILE
echo ""
echo "Script finished! Please check fix_psc_state.log"

