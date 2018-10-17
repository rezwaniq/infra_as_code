# infra_as_code 1.0

Initial setup to run this script:

Follow the link below to install Boto3 package and setup your laptop to run this script.
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html

Steps to run the script:
1. Fill out aws1_data.yaml file with info regarding your VPC, BGP etc. 
2. Most of the fields in this yaml file would stay same for subsequent creation of end to end infrastructure with a different DirectConnect connections.
3. Run the script aws1om.py from the same folder as the yaml file.



This script will create end to end infrastructur in AWS for NFV Cloud to Cloud test. It would do the following.
  a. Auto detects list of specific DirectConnect connections (using name pattern) from list of other people's connections. 
  b. Accepts those connections one by one so they change to 'Available' state from 'Acceptance Pending' state.
  c. Creates a Virtual Private Gateway
  d. Attaches that Virtual Private GW to a specific Virtual Privale Cloud (VPC). Recommended to use Default VPC so it has Subnets, IGW etc already there. Otherwise that has to be created manually.
  e. Creates DirectConnect Gateway
  f. Associates DirectConnect GW with Virtual Private GW
  g. Creates Virtual Interface
  f. Creates Virtual Machine in the specified VPC/Subnet.
