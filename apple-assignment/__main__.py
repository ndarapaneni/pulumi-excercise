"""An AWS Python Pulumi program"""

import pulumi
import json
import pulumi_aws as aws

# Configs
config = pulumi.Config()

ebs_volume_size = config.require("ebs_volume_size")
instance_type = config.require("instance_type")


#Create a new VPC
vpc = aws.ec2.Vpc("myVpc", cidr_block="10.0.0.0/16")

# Create a public route table
public_route_table = aws.ec2.RouteTable("publicRouteTable",
    vpc_id=vpc.id,
)

# Create a private route table
private_route_table = aws.ec2.RouteTable("privateRouteTable",
    vpc_id=vpc.id,
)

# Create an internet gateway
internet_gateway = aws.ec2.InternetGateway("internetGateway",
    vpc_id=vpc.id,
)

# Associate the public route table with the internet gateway
aws.ec2.Route("publicRoute",
    route_table_id=public_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=internet_gateway.id
)

# Create a public subnet associated with the public route table
public_subnet = aws.ec2.Subnet("publicSubnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="us-east-1a",
)

# Associate the route table public subnet
public_route_table_association = aws.ec2.RouteTableAssociation("PublicRouteTableAssociation",
    subnet_id=public_subnet.id,
    route_table_id=public_route_table.id)


# Create a private subnet associated with the private route table
private_subnet = aws.ec2.Subnet("privateSubnet",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="us-east-1a",
)

# Associate the route table Private subnet
private_route_table_association = aws.ec2.RouteTableAssociation("PrivateRouteTableAssociation",
    subnet_id=private_subnet.id,
    route_table_id=private_route_table.id)


# Create an S3 Bucket
apple_bucket = aws.s3.Bucket('apple-bucket')


#create IAM roles and s3 read only policy
ec2_role = aws.iam.Role("ec2Role",
    assume_role_policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sts:AssumeRole"
            ],
            "Principal": {
                "Service": [
                    "ec2.amazonaws.com"
                ]
            }
        }
    ]
}))


# S3 readonly policy
s3_list_policy = aws.iam.Policy("S3ReadOnlyPolicy",
    path="/",
    description="My test policy",
    policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:ListAllMyBuckets"
            ],
            "Resource": "*"
        }
    ]
}))

pulumi.export('policy_arn', s3_list_policy.arn)

# Attach a policy to the role
ec2_role_attach = aws.iam.PolicyAttachment("ec2RoleAttach",
    roles=[ec2_role.name],
    policy_arn=s3_list_policy.arn)

pulumi.export('ec2_role_attach', ec2_role_attach.name)

# Reading python script data
with open("create_numbers.py","r") as file:
  content=file.read()


# Create an instance profile from role to attach to an ec2
ec2_instance_profile = aws.iam.InstanceProfile("ec2InstanceProfile", role=ec2_role_attach.name)

# Security Group with public SSH access
sg_public_ssh = aws.ec2.SecurityGroup("SSHPublic",
    description="Allow SSH from Public",
    vpc_id = vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        from_port=22,
        to_port=22,
        protocol="tcp",
        cidr_blocks=["0.0.0.0/0"],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
    )],
    tags={
        "Name": "Allow_SSH_public"
    }
    )


#Creating Ec2 instance in public subnet
ec2_public = aws.ec2.Instance("ec2InstancePublic",
  ami = "ami-05c13eab67c5d8861",
  instance_type = instance_type,
  availability_zone = "us-east-1a",
  subnet_id=public_subnet.id,
  key_name = "apple-assignment",
  associate_public_ip_address = True,
  security_groups = [sg_public_ssh.id],
  tags={
        "Name": "EC2_Public",
    }
  )

# Create EC2 instance in the private subnet
ec2_private = aws.ec2.Instance("ec2InstancePrivate",
    ami = "ami-05c13eab67c5d8861",
    instance_type = instance_type,
    availability_zone = "us-east-1a",
    subnet_id=private_subnet.id,
    key_name = "apple-assignment",
    iam_instance_profile = ec2_instance_profile.name,

    ebs_block_devices = [{
       "deviceName": "/dev/xvdf",
       "volumeSize": ebs_volume_size,
       "volumeType": "gp2"
    }],
    
    user_data = f"""#!/bin/bash
    #Mounting the EBS volume
    mkdir /mnt/new-ebs-volume
    mkfs.ext4 /dev/xvdf
    mount /dev/xvdf /mnt/new-ebs-volume

    echo 'with open("/home/ec2-user/numbers.txt","w") as file:' > /home/ec2-user/numbers.py
    echo '  for number in range(1,101):' >> /home/ec2-user/numbers.py
    echo '    file.write(str(number)+"\\n")' >> /home/ec2-user/numbers.py
    
    python3 /home/ec2-user/numbers.py

    """,
    user_data_replace_on_change = True,
    tags={
        "Name": "EC2_Private",
    })

# Exports
pulumi.export("vpcId", vpc.id)
pulumi.export("vpc_cidr", vpc.cidr_block)
pulumi.export("public_route_table_id", public_route_table.id)
pulumi.export("private_route_table_id", private_route_table.id)
pulumi.export("internet_gateway_id", internet_gateway.id)
pulumi.export("public_subnet_id", public_subnet.id)
pulumi.export("private_subnet_id", private_subnet.id)
pulumi.export('s3_bucket_name', apple_bucket.id)
pulumi.export('IAM_role_name', ec2_role.name)
pulumi.export('EC2 Public IPv4', ec2_public.public_ip)
pulumi.export('EC2 Private IPv4', ec2_private.private_ip)



