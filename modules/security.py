#!/usr/bin/env python

import os

from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


class Security:
	"""To encrypt and/or sign communications between clients across a server"""

	KEY_PREFIX = "assist_"

	def __init__(self, nodename, keylength, keypath = "./"):
		self.nodename = str(nodename)
		self.keypath = keypath
		self.privkey = None
		self.pubkey = None
		self.keylength = keylength
		self.receiver_keys = dict()
	
	def create_key_pair(self):
		self.privkey = RSA.generate(self.keylength, Random.new().read)
		with open(self.keypath + self.KEY_PREFIX + self.nodename + "_priv", "w") as fpriv:
			fpriv.write(self.privkey.exportKey())
		with open(self.keypath + self.KEY_PREFIX + self.nodename + ".pub", "w") as fpub:
			fpub.write(self.privkey.publickey().exportKey())

	def load_my_privkey(self):
		keyfilename = self.keypath + self.KEY_PREFIX + self.nodename + "_priv"
		if os.path.exists(keyfilename):
			try:
				self.privkey = RSA.importKey(open(keyfilename, "r").read())
				return True
			except:
				self.privkey = None
				print("Error: invalid private key.")

	def load_my_pubkey(self):
		keyfilename = self.keypath + self.KEY_PREFIX + self.nodename + ".pub"
		if os.path.exists(keyfilename):
			try:
				self.pubkey = RSA.importKey(open(keyfilename, "r").read())
				return True
			except:
				self.pubkey = None
				print("Error: invalid public key.")

	def load_other_pubkey(self, other):
		keyfilename = self.keypath + self.KEY_PREFIX + other + ".pub"
		if os.path.exists(keyfilename):
			try:
				self.receiver_keys[other] = RSA.importKey(open(keyfilename, "r").read())
				return True
			except:
				self.receiver_keys[other] = None
				print("Error: invalid public key.")

	def encrypt(self, target, message):
		if not target in self.receiver_keys:
			key_loaded = self.load_other_pubkey(target)
			if not key_loaded:
				print("Error: could not load public key of '{}'.".format(target))
				return
		return self.receiver_keys[target].encrypt(message, 32)

	def decrypt(self, data):
		if not self.privkey:
			if not self.load_my_privkey():
				print("Error: could not locate your private key.")
				return
		return self.privkey.decrypt(data)

	def calc_signature(self, message):
		if not self.privkey:
			if not self.load_my_privkey():
				print("Error: could not locate your private key.")
				return
		sha_hash = SHA256.new(message).digest()
		return self.privkey.sign(sha_hash, "")

	def verify_signature(self, sender, message, signature):
		if not sender in self.receiver_keys:
			key_loaded = self.load_other_pubkey(sender)
			if not key_loaded:
				print("Error: could not load public key of '{}'.".format(sender))
				return
		sha_hash = SHA256.new(message).digest()
		return self.receiver_keys[sender].sign(sha_hash, signature)
