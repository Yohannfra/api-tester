# Api-Tester

## Installation

#### Dependencies:

```bash
$ python3 -m pip install -r requirements.txt
```

## Usage

### Run example

```
$ ./api-tester.py examples/test_jsonplaceholder_api.json
```

### Cli args

```bash
$ ./api-tester.py  -h
usage: api-tester [-h] [-v {2,1}] [--host HOST] [--headers KEY=VALUE [KEY=VALUE ...]] test_file

A python program to test an api based on a json configuration file

positional arguments:
  test_file

optional arguments:
  -h, --help            show this help message and exit
  -v {2,1}, --verbose-level {2,1}
                        2: default verebosity level that prints everything, 1: hide test diff when a test fails
  --host HOST           Override host values in json config file
  --headers KEY=VALUE [KEY=VALUE ...]
                        headersAdd values into global headers(do not put spaces before or after the = sign). If a
                        value contains spaces, you should define it with double quotes:

```
