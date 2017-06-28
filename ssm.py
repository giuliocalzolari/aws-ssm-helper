#!/usr/bin/env python

import time
import os
import boto3
import botocore
import json
import sys
import argparse
from termcolor import colored
from datetime import datetime, timedelta

ACCOUNT = {
    "dev": "111111111111",
    "stage": "222222222222",
    "prod": "3333333333333"
}


class SSMRunner(object):

    def __init__(self, args):

        self.cfg = args
        self.cfg.credentials = {}
        self.ssm = self.get_client('ssm')

    def get_client(self, service):

        if self.cfg.iam == "":
            return boto3.client(service, region_name=self.cfg.region)

        if self.cfg.iam == "auto":
            self.cfg.iam = "arn:aws:iam::{}:role/role-admin".format(ACCOUNT[self.cfg.stage])

        if self.cfg.credentials == {}:
            print "assume Role: {}".format(self.cfg.iam)
            sts_client = boto3.client("sts")
            self.cfg.credentials = sts_client.assume_role(
                RoleArn=self.cfg.iam,
                RoleSessionName="ssm-run")["Credentials"]

        return boto3.client(
            service,
            region_name=self.cfg.region,
            aws_access_key_id=self.cfg.credentials["AccessKeyId"],
            aws_secret_access_key=self.cfg.credentials["SecretAccessKey"],
            aws_session_token=self.cfg.credentials["SessionToken"])

    def renew_sts(self):

        if self.cfg.iam == "":
            return

        if datetime.strptime(str(self.cfg.credentials["Expiration"]), '%Y-%m-%d %H:%M:%S+00:00') < datetime.utcnow():
            print "Renew STS: {}".format(iam)
            sts_client = boto3.client("sts")
            self.cfg.credentials = sts_client.assume_role(
                RoleArn=self.cfg.iam,
                RoleSessionName="ssm-run")["Credentials"]

    def run(self):
        target_str = self.cfg.target.split("=")

        target = [{
            'Key': target_str[0],
            'Values': target_str[1].split(",")
        }]

        command = self.ssm.send_command(
            Targets=target,
            DocumentName='AWS-RunShellScript',
            Parameters={
                "commands": [self.cfg.command]
            },
            TimeoutSeconds=self.cfg.timeout
        )

        status = 'Pending'

        while status == 'Pending' or status == 'InProgress':

            self.renew_sts()
            running_cmd = self.ssm.list_commands(
                CommandId=command['Command']['CommandId'])
            status = running_cmd['Commands'][0]['Status']
            # print running_cmd
            time.sleep(1)

        results = self.ssm.list_command_invocations(
            CommandId=running_cmd['Commands'][0]['CommandId']
        )

        for result in results["CommandInvocations"]:

            output = self.ssm.get_command_invocation(
                CommandId=running_cmd['Commands'][0]['CommandId'],
                InstanceId=result["InstanceId"],
            )
            if result["Status"] == "Success":
                print "[Command run on {} result: {}]".format(
                    colored(result["InstanceId"], 'cyan'),
                    colored(result["Status"], 'green')
                )
                print sys.stdout.write(output.get("StandardOutputContent", ""))
            elif result["Status"] == "Failed":
                print "[Command run on {} result: {}]".format(
                    colored(result["InstanceId"], 'cyan'),
                    colored(result["Status"], 'red')
                )
                print sys.stdout.write(output.get("StandardOutputContent", ""))
                print sys.stdout.write(output.get("StandardErrorContent", ""))
            else:
                print colored("NOT SURE", "yellow")
                print output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='SSM Run Helper')
    parser.add_argument('--stage', default="dev", help='stage')
    parser.add_argument('--region', default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-1"), help='AWS region')
    parser.add_argument('--command', help='command')
    parser.add_argument('--target', help='target')
    parser.add_argument('--timeout', default=30, help='timeout')
    parser.add_argument('--iam', default="auto", help='IAM to assume')
    args = parser.parse_args()

    try:
        task = SSMRunner(args)
        task.run()
    except KeyboardInterrupt:
        print "quit"
