#!/usr/bin/env python3

import os
import sys
import json
from typing import List, Dict
import requests
import colored
import argparse
from colored import stylize

# 2 Default | 1 Quiet
VERBOSE_LEVEL = 2

METHOD_NAME_TO_FUNCTION = {
    'GET': requests.get,
    'HEAD': requests.head,
    'POST': requests.post,
    'PUT': requests.put,
    'PATCH': requests.patch,
    'DELETE': requests.delete,
}


class HttpTester:
    def __init__(self, host: str, test_list: List[object], global_headers: Dict[str, str]):
        self.host = host
        self.test_list = test_list
        self.global_headers = global_headers

        self.nb_tests = 0
        self.nb_tests_failed = 0

        print(f"Testing {host}\n")

    def print_test_fail(self, msg: str):
        self.nb_tests_failed += 1
        if VERBOSE_LEVEL == 2:
            # TODO, print better diff
            print(f"{msg} {stylize('KO', colored.fg('red'))}")
        else:
            print(f"{stylize('KO', colored.fg('red'))}")

    def run(self):
        # dry run to check tests before running any
        for test in self.test_list:
            self.validate_test_content(test)

        for test in self.test_list:
            print(f"{test['name']}:", end=' ')

            if 'skip' in test and test['skip'] == True:
                print(f"{stylize('SKIPPED', colored.fg('orange_4b'))}")
                continue

            # prepare request content
            methods, full_url, params, headers, body = self.prepare_test(test)

            if len(methods) > 1:
                print("")

            for method in methods:
                self.nb_tests += 1
                if len(methods) > 1:
                    print(f"  {method}\t", end='')

                # run request
                result = METHOD_NAME_TO_FUNCTION[method](
                    full_url, params=params, headers=headers, data=body)
                # check test result
                self.check_result(test, result)

        self.print_summary()
        return self.nb_tests_failed

    def check_result(self, test, result: requests.Response):
        # If there is no response object in test json, maybe we want to run some request without testing it
        if 'response' not in test:
            print(f"{stylize('-', colored.fg('orange_4b'))}")
            return

        # check http code
        if 'code' in test['response'] and test['response']['code'] != result.status_code:
            return self.print_test_fail(f"Expected status {test['response']['code']} but got {result.status_code}")

        # check nb items
        if 'nb_json_items' in test['response'] and len(result.json()) != test['response']['nb_json_items']:
            return self.print_test_fail(f"Expected {test['response']['nb_json_items']} json items but got {len(result.json())}")

        # check json content exact
        if 'content-json-exact' in test['response'] and json.loads(result.content) != test['response']['content-json-exact']:
            return self.print_test_fail(f"Expected {test['response']['content-json-exact']} but got {json.loads(result.content)}")

        print(f"{stylize('OK', colored.fg('green'))}")

    def print_summary(self):
        """ print a summary of the tests results """
        count_success = self.nb_tests - self.nb_tests_failed
        print(f"\nSummary {self.host}: {self.nb_tests} tests ran")
        print(f"{count_success} : {stylize('OK', colored.fg('green'))}")
        print(f"{self.nb_tests_failed} : {stylize('KO', colored.fg('red'))}")

    def validate_test_content(self, test):
        if 'name' not in test:
            sys.exit("Missing 'name' key in test")

        if 'method' not in test and 'methods' not in test:
            sys.exit(f"{test['name']}: Missing 'method' or 'methods' key")
        else:
            if 'method' in test and 'methods' in test:
                sys.exit(
                    f"{test['name']}: A test can't have both 'method' and 'methods' defined")

        if 'endpoint' not in test:
            sys.exit(f"{test['name']}: Missing 'endpoint' key")

    def prepare_test(self, test):
        # method
        if 'methods' in test:
            methods = test['methods']
        else:
            methods = [test['method']]

        # url
        full_url = self.host + test['endpoint']

        # query params
        if 'queries' in test:
            params = test['queries']
        else:
            params = {}

        # body
        if 'body' in test:
            body = json.dumps(test['body'])
        else:
            body = "{}"

        # headers
        headers = self.global_headers
        if 'headers' in test:
            headers = {**self.global_headers, **test['headers']}

        return methods, full_url, params, headers, body


class CliParser:
    def __init__(self):
        pass

    def __new__(cls):
        parser = argparse.ArgumentParser(
            prog='api-tester',
            description=' A python program to test an api based on a json configuration file'
        )
        parser.add_argument('test_file')
        parser.add_argument('-v', '--verbose-level', choices=['2', '1'], default='2',
                            help='2: default verebosity level that prints everything, 1: hide test diff when a test fails'
                            )
        parser.add_argument(
            '--host', help='Override host values in json config file')
        parser.add_argument("--headers",
                            metavar="KEY=VALUE",
                            nargs='+',
                            help="headers"
                            "Add values into global headers"
                            "(do not put spaces before or after the = sign). "
                            "If a value contains spaces, you should define it with double quotes: ")

        args = parser.parse_args()
        return {
            'test_file': args.test_file,
            'host': args.host,
            'verbose_level': args.verbose_level,
            'headers': CliParser.parse_vars(args.headers),
        }

    def parse_var(s):
        """
        Parse a key, value pair, separated by '='

        On the command line (argparse) a declaration will typically look like:
            foo=hello
        or
            foo="hello world"
        """
        items = s.split('=')
        key = items[0].strip()  # remove blanks around keys
        if len(items) > 1:
            # rejoin the rest:
            value = '='.join(items[1:])
        return (key, value)

    def parse_vars(items):
        """
        Parse a series of key-value pairs and return a dictionary
        """
        d = {}
        if items:
            for item in items:
                key, value = CliParser.parse_var(item)
                d[key] = value
        return d


def main() -> None:
    global VERBOSE_LEVEL

    cli_args = CliParser()

    VERBOSE_LEVEL = int(cli_args['verbose_level'])

    json_content = None
    with open(cli_args['test_file'], "r") as f:
        json_content = json.loads(f.read())

    # get host
    if 'host' not in json_content:
        sys.exit("Missing 'host' global key")
    host = json_content['host']
    if cli_args['host'] != None:
        host = cli_args['host']

    # get test list
    if 'tests' not in json_content:
        sys.exit("Missing 'tests' global key")
    tests = json_content['tests']

    # get headers
    if 'headers' in json_content:
        headers = json_content['headers']
    else:
        headers = {}
    if cli_args['headers'] != None:
        headers = {**headers, **cli_args['headers']}

    tester = HttpTester(host, tests, headers)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
