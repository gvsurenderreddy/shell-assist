#!/usr/bin/env python

import sys
import os
import argparse

from modules import security
from modules import connection


class Client:
	"""assist-client class"""

	def __init__(self):
		self.conn = connection.Connection()
		self.sec = security.Security()
