#!/usr/bin/env python
"""Summary
"""

import time
import os
import boto3
import botocore
import sys
import argparse
from termcolor import colored
from datetime import datetime, timedelta
import logging

# Setup simple logging for INFO
logger = logging.getLogger("ssm-run")
for h in logger.handlers:
    logger.removeHandler(h)
h = logging.StreamHandler(sys.stdout)
FORMAT = "[%(asctime)s][%(levelname)s] %(message)s"
h.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(h)
logger.setLevel(logging.INFO)


class SSMRunner(object):
    """Summary

    Attributes:
        cfg (object): Config with all related parameters
        ssm (boto3.client): SSM boto3.client
        target (list): SSM target
    """

    def __init__(self, args):
        """Init class

        Args:
            args (TYPE): Description
        """
        self.cfg = args
        self.cfg.credentials = {}
        if args.verbose:
            logger.setLevel(logging.DEBUG)
        try:
            self.ssm = self.get_client("ssm")
        except botocore.exceptions.ClientError as e:
            logger.critical(e)
            exit(1)

    def get_client(self, service):
        """boto3.client helper
        can return a simple boto3.client or execute an sts assume_role action

        Args:
            service (string): AWS service 

        Returns:
            boto3.client: client to execute action into a specific account and region
        """
        if self.cfg.iam == "":
            return boto3.client(service, region_name=self.cfg.region)

        if self.cfg.credentials == {}:
            logger.info("assume Role: {}".format(self.cfg.iam))
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
        """Automatic refresh of the sts in case the session expire for any reason
        the token is renewed one minute before the real expiration 

        Returns:
            None
        """
        if self.cfg.iam == "":
            return

        expire_date = datetime.strptime(
            str(self.cfg.credentials["Expiration"]), "%Y-%m-%d %H:%M:%S+00:00")
        if expire_date - timedelta(minutes=1) < datetime.utcnow():
            logger.info("Renew STS: {}".format(iam))
            sts_client = boto3.client("sts")
            self.cfg.credentials = sts_client.assume_role(
                RoleArn=self.cfg.iam,
                RoleSessionName="ssm-run")["Credentials"]

    def get_target(self):
        """Parsing string to define the Target to send the command
        for additional info please read here
        http://docs.aws.amazon.com/systems-manager/latest/userguide/send-commands-multiple.html

        Returns:
            list of dictionary: Target to filter the instaces registered into SSM
        """
        self.target = []
        for tags in self.cfg.target.split(","):
            t = tags.split("=")
            self.target.append({
                "Key": t[0],
                "Values": [t[1]]
            })

        return self.target

    def run(self):
        """Main command
        """

        logger.debug("send_command : {}".format(self.cfg.command))
        command = self.ssm.send_command(
            Targets=self.get_target(),
            DocumentName="AWS-RunShellScript",
            Parameters={
                "commands": [self.cfg.command]
            },
            TimeoutSeconds=self.cfg.timeout
        )

        status = "Pending"
        while status == "Pending" or status == "InProgress":

            self.renew_sts()
            logger.debug("get status of command: {}".format(
                command["Command"]["CommandId"]))
            running_cmd = self.ssm.list_commands(
                CommandId=command["Command"]["CommandId"])
            status = running_cmd["Commands"][0]["Status"]
            # print running_cmd
            time.sleep(1)

        logger.debug("get the full output of command: {}".format(
            command["Command"]["CommandId"]))
        results = self.ssm.list_command_invocations(
            CommandId=running_cmd["Commands"][0]["CommandId"]
        )

        for result in results["CommandInvocations"]:

            logger.debug("retrieve command {} invoked in: {}".format(
                command["Command"]["CommandId"], result["InstanceId"]))
            output = self.ssm.get_command_invocation(
                CommandId=running_cmd["Commands"][0]["CommandId"],
                InstanceId=result["InstanceId"],
            )
            if result["Status"] == "Success":
                logger.info("Command run on {} result: {}".format(
                    colored(result["InstanceId"], "cyan"),
                    colored(result["Status"], "green")
                ))
                sys.stdout.write(output.get("StandardOutputContent", ""))
            elif result["Status"] == "Failed":
                logger.error("Command run on {} result: {}".format(
                    colored(result["InstanceId"], "cyan"),
                    colored(result["Status"], "red")
                ))
                sys.stdout.write(output.get("StandardOutputContent", ""))
                sys.stdout.write(output.get("StandardErrorContent", ""))
            else:
                logger.warning(colored("NOT SURE", "yellow"))
                print output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="SSM Run Helper")
    parser.add_argument(
        "--region", default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-1"), help="AWS region")
    parser.add_argument("--command", help="command")
    parser.add_argument("--target", help="target")
    parser.add_argument("--timeout", default=30, help="timeout")
    parser.add_argument(
        "--iam", default=os.environ.get("AWS_SSM_ROLE", ""), help="IAM to assume")
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()

    try:
        task = SSMRunner(args)
        task.run()
    except KeyboardInterrupt:
        print "quit"
