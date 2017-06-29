# AWS SSM helper

## Package dependencies

 - `boto3`
 - `botocore`
 
in order to simplify the managerment of your EC2 instances I strongly suggest to install SSM everywhere following the main [documentation](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/tutorial_run_command.html)

Using SSM you can run quickly any command 

## Config

this script is designed to run across multiple accounts and across multiple regions you can switch between regions/accounts using some OS vars

To execute an assume role action

`$ export AWS_SSM_ROLE=arn:aws:iam::111111111:role/admin`

To Set the related region

`$ export AWS_DEFAULT_REGION=eu-west-1`


### Example
update your package in your bastion host

`$ ./ssm.py --target tag:Name=bastion-host --command "apt-get update -y"
`

install python in your DEV enviroment 

`$ ./ssm.py --target tag:Environment=DEV --command "apt-get install python -y"
`

you can use multiple tags divided by `,` for example

`$ ./ssm.py --target tag:Name=web-asg,tag:Environment=DEV --command "apt-get install python -y"
`


### Command

```
$ ./ssm.py -h
usage: SSM Run Helper [-h] [--region REGION] [--command COMMAND]
                      [--target TARGET] [--timeout TIMEOUT] [--iam IAM] [-v]

optional arguments:
  -h, --help         show this help message and exit
  --region REGION    AWS region
  --command COMMAND  command
  --target TARGET    target
  --timeout TIMEOUT  timeout
  --iam IAM          IAM to assume
  -v, --verbose      increase output verbosity
   
```

## License

**aws-ssm-helper** is licensed under the [MIT](LICENSE).