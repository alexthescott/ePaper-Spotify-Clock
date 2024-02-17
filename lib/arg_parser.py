import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-v', action='store_true', help='Enable Verbose Logging')
parser.add_argument('--clock', action='store_true', help='Enable clock')
parser.add_argument('--local', action='store_true', help='Force write to test_output/')

args = parser.parse_args()
