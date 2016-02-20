#!/usr/bin/env python3

import sys
import os
import argparse

from modules import connection


def main():
	if len(sys.argv) == 3:
		assist_client = connection.ClientConnection(sys.argv[1], sys.argv[2])
		assist_client.connect_to_server()

if __name__ == "__main__":
	main()
