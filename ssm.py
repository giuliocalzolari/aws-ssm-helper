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


class SSMRunner(object):

    def __init__(self, args):

        self.cfg = args
        self.cfg.credentials = {}
        self.ssm = self.get_client('ssm')

    def get_client(self, service):

        if self.cfg.iam == "":
            return boto3.client(service, region_name=self.cfg.region)

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

    def get_target(self):
        self.target = []
        for tags in  self.cfg.target.split(","):
            t = tags.split("=")
            self.target.append({
                'Key': t[0],
                'Values': [t[1]]
            })

        return self.target

    def run(self):

        command = self.ssm.send_command(
            Targets=self.get_target(),
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
                print "\n[Command run on {} result: {}]".format(
                    colored(result["InstanceId"], 'cyan'),
                    colored(result["Status"], 'green')
                )
                sys.stdout.write(output.get("StandardOutputContent", ""))
            elif result["Status"] == "Failed":
                print "\n[Command run on {} result: {}]".format(
                    colored(result["InstanceId"], 'cyan'),
                    colored(result["Status"], 'red')
                )
                sys.stdout.write(output.get("StandardOutputContent", ""))
                sys.stdout.write(output.get("StandardErrorContent", ""))
            else:
                print colored("NOT SURE", "yellow")
                print output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='SSM Run Helper')
    parser.add_argument('--region', default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-1"), help='AWS region')
    parser.add_argument('--command', help='command')
    parser.add_argument('--target', help='target')
    parser.add_argument('--timeout', default=30, help='timeout')
    parser.add_argument('--iam', default=os.environ.get("AWS_SSM_ROLE", ""), help='IAM to assume')
    args = parser.parse_args()

    try:
        task = SSMRunner(args)
        task.run()
    except KeyboardInterrupt:
        print "quit"
