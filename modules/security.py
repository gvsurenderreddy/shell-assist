#!/usr/bin/env python

import os

from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


class Security:
	"""To encrypt and/or sign communications between clients across a server"""

	KEY_PREFIX = "assist_"

	def __init__(self, username = "me", keypath = "./"):
		self.username = str(username)
		self.keypath = keypath
		self.privkey = None
		self.pubkey = None
		self.receiver_keys = dict()
	
	def create_key_pair(self):
		self.privkey = RSA.generate(4096, Random.new().read)
		with open(self.keypath + self.KEY_PREFIX + self.username + "_priv", "w") as fpriv:
			fpriv.write(self.privkey.exportKey())
		with open(self.keypath + self.KEY_PREFIX + self.username + ".pub", "w") as fpub:
			fpub.write(self.privkey.publickey().exportKey())

	def load_my_privkey(self):
		keyfilename = self.keypath + self.KEY_PREFIX + self.username + "_priv"
		if os.path.exists(keyfilename):
			try:
				self.privkey = RSA.importKey(open(keyfilename, "r").read())
			except:
				self.privkey = None
				print("Error: invalid private key.")

	def load_my_pubkey(self):
		keyfilename = self.keypath + self.KEY_PREFIX + self.username + ".pub"
		if os.path.exists(keyfilename):
			try:
				self.pubkey = RSA.importKey(open(keyfilename, "r").read())
			except:
				self.pubkey = None
				print("Error: invalid public key.")

	def load_other_pubkey(self, other = "anon"):
		keyfilename = self.keypath + self.KEY_PREFIX + other + ".pub"
		if os.path.exists(keyfilename):
			try:
				self.receiver_keys[other] = RSA.importKey(open(keyfilename, "r").read())
			except:
				self.receiver_keys[other] = None
				print("Error: invalid public key.")
