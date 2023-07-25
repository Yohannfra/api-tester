#!/usr/bin/env python3

import os
import sys
import json
from typing import List, Dict
import requests
import colored
from colored import stylize

# 0 Normal | 1 Quiet | 2 Super Quiet
QUIET_LEVEL = 0

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
        print(f"{msg} {stylize('KO', colored.fg('red'))}")

    def run(self):
        for test in self.test_list:
            print(f"{test['name']}:", end=' ')

            if 'skip' in test and test['skip'] == True:
                print(f"{stylize('SKIPPED', colored.fg('orange_4b'))}")
                continue

            self.nb_tests += 1

            # prepare request content
            method, full_url, params, headers, body = self.prepare_test(test)

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
        if QUIET_LEVEL == 2:
            if self.nb_tests_failed > 0:
                print(f"{self.host}: {stylize('KO', colored.fg('red'))}")
            else:
                print(f"{self.host}: {stylize('OK', colored.fg('green'))}")
        else:
            count_success = self.nb_tests - self.nb_tests_failed
            print(f"\nSummary {self.host}: {self.nb_tests} tests ran")
            print(f"{count_success} : {stylize('OK', colored.fg('green'))}")
            print(f"{self.nb_tests_failed} : {stylize('KO', colored.fg('red'))}")

    def prepare_test(self, test):
        # method
        if 'method' not in test:
            sys.exit("Missing 'method' key in test")
        method = test['method']

        # url
        if 'endpoint' not in test:
            sys.exit("Missing 'endpoint' key in test")
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

        return method, full_url, params, headers, body


def main(argc: int, argv: List[str]) -> None:
    if argc != 2:
        sys.exit(f"USAGE {argv[0]} test_file.json")

    json_content = None
    with open(argv[1], "r") as f:
        json_content = json.loads(f.read())

    # get host
    if 'host' not in json_content:
        sys.exit("Missing 'host' global key")
    host = json_content['host']

    # get test list
    if 'tests' not in json_content:
        sys.exit("Missing 'tests' global key")
    tests = json_content['tests']

    # get headers
    if 'headers' in json_content:
        headers = json_content['headers']
    else:
        headers = {}

    tester = HttpTester(host, tests, headers)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
