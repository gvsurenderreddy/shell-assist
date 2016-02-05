#!/usr/bin/env python

import sys
import os
import argparse

from modules import security
from modules import connection


class Client:
	"""assist-client class"""

	def __init__(self):
		self.sec = security.Security()


def main():
	if len(sys.argv) == 3:
		assist_client = connection.ClientConnection(sys.argv[1], sys.argv[2])
		assist_client.connect_to_server()

if __name__ == "__main__":
	main()
