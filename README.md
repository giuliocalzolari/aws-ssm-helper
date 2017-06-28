# AWS SSM helper

## Package dependencies

 - `boto3`
 - `botocore`
 
in order to simplify the managerment of your EC2 instances I strongly suggest to install SSM everywhere following the main [documentation]
(http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/tutorial_run_command.html)

Using SSM you can run quickly any command 

### Example
update your package in your bastion host

`./ssm.py --target tag:Name=bastion-host --command "apt-get update -y"
`

install python in your DEV enviroment 

`./ssm.py --target tag:Environment=DEV --command "apt-get install python -y"
`


## License

**aws-ssm-helper** is licensed under the [MIT](LICENSE).