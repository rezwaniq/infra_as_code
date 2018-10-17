import sys
import boto3
import yaml
from botocore.exceptions import ClientError
import random
import time

#Generating random number to avoid deletion(Remove it in the production)
random_number = str(random.randint(1, 100000))
default_vpc_id = ''
global_input_data = None
dns_name = None


def getInputData():
    with open("aws1_data.yaml", 'r') as stream:
        try:
            input_data = yaml.load(stream)
            global global_input_data
            global_input_data = input_data
            print(input_data)
            return input_data
        except yaml.YAMLError as exc:
            print(exc)  

#client = boto3.client('directconnect')
#client_ec2 = boto3.client('ec2')

##In my Instruction manual VPG creation is later down the line (page 6), however there can be only 5 VPG per acc initially so I am creating one in the begining to see there is bandwidth or not.
##Creating VPG.
def create_vpn_gateway():
	input_data = global_input_data
	client_ec2 = boto3.client('ec2')
	
	vpn_gw_creation_resp = client_ec2.create_vpn_gateway(
		Type='ipsec.1',
		AmazonSideAsn=input_data['vpg_detail']['AmazonSideAsn'],
		DryRun=False
	)

	print (vpn_gw_creation_resp)
	print ("Creating Virtual Private Gateway... ")
	print("Created VPG " + vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"])
	return vpn_gw_creation_resp


#Attach the VPG to your VPC. Create a VPC manually and provide its ID and VPG ID in the function below
def attach_vpn_gateway(vpn_gw_creation_resp):
    input_data = global_input_data
    client_ec2 = boto3.client('ec2')
    print(input_data['vpc_detail']['def_vpc_id'])
    your_vpc_id= str(input_data['vpc_detail']['def_vpc_id'])
    vpg_vpc_attach_resp = client_ec2.attach_vpn_gateway(
            VpcId=your_vpc_id,
            VpnGatewayId=vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"],
            DryRun=False
    )

    print("VPG" + vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"] + " is attahed to VPC " + your_vpc_id)


#Listing all the DC(Directconnect) connections in the account 
def describe_connections():
    input_data = global_input_data
    client = boto3.client('directconnect')
    dc_describe_response = client.describe_connections()
    print(dc_describe_response)
    return dc_describe_response

#Matching connections with name pattern from yaml and checking if the state is "pending acceptance (aka "ordering"). If yes then accepting those connections one by one
def confirm_connection(dc_describe_response):
    input_data = global_input_data
    client = boto3.client('directconnect')
    default_connection = None
    default_connection_name = str(input_data['virtual_int_detail']['dc_name'])#'NSD_AWS_SV_TEST'
    for result in dc_describe_response["connections"]:
	    if result["connectionName"] == default_connection_name:
	        default_connection = result	    
	    if str(input_data['your_direct_conn_detail']['conn_match_pattern']) in result["connectionName"]:
			    print ("Found "+result["connectionName"])
			    if result["connectionState"] == "ordering":
				    dc_conn_confirm_resp = client.confirm_connection(connectionId=result["connectionId"])				    
				    print ("Accepted Direct Connect" + result["connectionName"])
				    print ("Check the status in AWS Console to verify")
				    
    return default_connection
				    

#Creating DCG with random name and same ASN-64515
def create_direct_connect():
    input_data = global_input_data
    client = boto3.client('directconnect')
    dc_gw_name= str(input_data['dc_gw']['name']) +random_number
    dc_gw_creation_resp = client.create_direct_connect_gateway(directConnectGatewayName=str(dc_gw_name), amazonSideAsn=65000)
    print("Creating DCG " + dc_gw_name)
    print("DCG" + dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"] + "created")
    return dc_gw_creation_resp;

#Creates association with DCG and VPG. Takes ~7 minutes
def create_direct_connect_association(dc_gw_creation_resp, vpn_gw_creation_resp):
    input_data = global_input_data
    client = boto3.client('directconnect')
    dc_gw_vpg_assoc_resp = client.create_direct_connect_gateway_association(
            directConnectGatewayId=dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"],
            virtualGatewayId=vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"]
    )

    print(dc_gw_vpg_assoc_resp)
    print("State is... " + dc_gw_vpg_assoc_resp["directConnectGatewayAssociation"]["associationState"])

    print ("Associating DCG " + dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"] + " and VPG " + vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"])

    #desp_dc_gw_assoc = client.describe_direct_connect_gateway_associations(
	    #directConnectGatewayId=dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"],
	    #virtualGatewayId=vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"],
	    #)

    #print("Association State: " + desp_dc_gw_assoc["directConnectGatewayAssociations"]["associationState"])
    #while desp_dc_gw_assoc["directConnectGatewayAssociations"]["associationState"]=="associating":              
	    #print('.', end='')
	    #time.sleep(5)
	    #desp_dc_gw_assoc = client.describe_direct_connect_gateway_associations(
		    #directConnectGatewayId=dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"],
		    #virtualGatewayId=vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"],
		    #)    
	    #if desp_dc_gw_assoc["directConnectGatewayAssociation"]["associationState"]=="associated":
		    #break

    #time.sleep(120)
    print("DCG " + dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"] + " and VPG " + vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"] + " in the process of associating")  

    print("Starting to create Virtual Interface")


#Create a Virtual Interface and fill out the details. 
def create_virtual_interface(dc_gw_creation_resp, default_connection):
    input_data = global_input_data
    client = boto3.client('directconnect')
    #default_describe_connection =client.describe_connections(connectionId=default_connection_id)   
    print('=======default_connection====')
    print(default_connection)   
    
    myownerAccount=default_connection["ownerAccount"] 
    myvlan=default_connection["vlan"]                                                        
    myasn= input_data['virtual_int_detail']['asn']
    myvirtualInterfaceName = str(input_data['virtual_int_detail']['virtualInterfaceName'])
    myauthKey=str(input_data['virtual_int_detail']['authKey'])
    myamazonAddress=str(input_data['virtual_int_detail']['amazonAddress'])
    mycustomerAddress=str(input_data['virtual_int_detail']['customerAddress'])

    create_virt_int_resp = client.create_private_virtual_interface(
	            connectionId=default_connection["connectionId"],
	            newPrivateVirtualInterface={
	                    'virtualInterfaceName': myvirtualInterfaceName,
	                    'vlan': myvlan,
	                    'asn': myasn,
	                    'authKey': myauthKey,
	                    'amazonAddress': myamazonAddress,
	                    'customerAddress': mycustomerAddress,
	                    'addressFamily': 'ipv4',
	                    #'virtualGatewayId': vpn_gw_creation_resp["VpnGateway"]["VpnGatewayId"],
	                    'directConnectGatewayId': dc_gw_creation_resp["directConnectGateway"]["directConnectGatewayId"]
	            }
	    )
    
    
    print(create_virt_int_resp)
    
    print("virt int ID:" + create_virt_int_resp["virtualInterfaceId"])
    print("virt GW ID: " + create_virt_int_resp["virtualGatewayId"])
    print ("Direct Connect GW ID: " + create_virt_int_resp["directConnectGatewayId"])

def create_ec2():
    input_data = global_input_data
    ##Creating EC2
    ec2 = boto3.resource('ec2')
    ec2_created = ec2.create_instances(
            BlockDeviceMappings=[
                    {
                            'DeviceName': '/dev/sdh',
                            'VirtualName': 'ephemeral0',
                            'Ebs': {
                                    'DeleteOnTermination': True,
                                    #'Iops': 100,
                                    #'SnapshotId': 'snapshot_1',
                                    'VolumeSize': 8,
                                    'VolumeType': 'standard',
                                    'Encrypted': False,
                                    
                            },
                            
                    },
            ],
            ImageId='ami-04534c96466647bfb',
            InstanceType='t2.micro',
            KeyName='testuser_key',
            MaxCount=1,
            MinCount=1,
            Monitoring={
                    'Enabled': True
            },
            
            SecurityGroupIds=[
                    'sg-05d53611c9c387705',
            ],
            
            SubnetId='subnet-717e5b2a',                  
            #UserData='string',
            DisableApiTermination=False,
            InstanceInitiatedShutdownBehavior='stop',
               
    )

    print("EC2 created: " + str(ec2_created))
	
getInputData()

#Creating Virtual Private GW
vpn_gw_creation_resp = create_vpn_gateway()

#Attaching VP GW
attach_vpn_gateway(vpn_gw_creation_resp)
describe_connections = describe_connections()
default_connection = confirm_connection(describe_connections)
dc_gw_creation_resp = create_direct_connect()
create_direct_connect_association(dc_gw_creation_resp, vpn_gw_creation_resp)
create_virtual_interface(dc_gw_creation_resp, default_connection)
create_ec2()