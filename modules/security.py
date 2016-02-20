#!/usr/bin/env python3

import sys
import os

from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


ENCODING = "utf-16"


class Security:
	"""To encrypt and/or sign communications between clients across a server"""

	SERVER_PREFIX = "server_"
	CLIENT_PREFIX = "client_"

	def __init__(self, nodename, keylength, is_server, keypath = "./keys/"):
		self.nodename = str(nodename)
		self.keypath = keypath
		self.privkey = None
		self.pubkey = None
		self.keylength = keylength
		self.receiver_keys = {}
		self.prefix = self.SERVER_PREFIX if is_server else self.CLIENT_PREFIX
	
	def create_key_pair(self, is_server = False):
		self.is_server = is_server
		if not os.path.exists(self.keypath):
			try:
				os.makedirs(self.keypath)
			except:
				print("Error: could not create 'keys' folder.")
				sys.exit(1)
		print("Generating public/private key pair. This may take a moment...")
		self.privkey = RSA.generate(self.keylength, Random.new().read)
		self.pubkey = self.privkey.publickey()
		print("Key pair created.")
		with open(self.keypath + self.prefix + self.nodename + ".priv", "wb") as fpriv:
			fpriv.write(self.privkey.exportKey())
		with open(self.keypath + self.prefix + self.nodename + ".pub", "wb") as fpub:
			fpub.write(self.privkey.publickey().exportKey())

	def my_key_pair_exists(self):
		privfilename = self.keypath + self.prefix + self.nodename + ".priv"
		pubfilename = self.keypath + self.prefix + self.nodename + ".pub"
		return os.path.exists(privfilename) and os.path.exists(pubfilename)

	def load_my_privkey(self):
		keyfilename = self.keypath + self.prefix + self.nodename + ".priv"
		if os.path.exists(keyfilename):
			try:
				self.privkey = RSA.importKey(open(keyfilename, "rb").read())
				return True
			except:
				self.privkey = None
				print("Error: invalid private key.")

	def load_my_pubkey(self):
		keyfilename = self.keypath + self.prefix + self.nodename + ".pub"
		if os.path.exists(keyfilename):
			try:
				self.pubkey = RSA.importKey(open(keyfilename, "rb").read())
				return True
			except:
				self.pubkey = None
				print("Error: invalid public key.")
		elif self.privkey:
			self.pubkey = self.privkey.publickey()
			with open(self.keypath + self.prefix + self.nodename + ".pub", "wb") as fpub:
				fpub.write(self.pubkey.exportKey())
			return True

	def load_other_pubkey(self, other):
		keyfilename = self.keypath + self.prefix + other + ".pub"
		if os.path.exists(keyfilename):
			try:
				self.receiver_keys[other] = RSA.importKey(open(keyfilename, "rb").read())
				return True
			except:
				self.receiver_keys[other] = None
				print("Error: invalid public key.")

	def save_other_pubkey(self, strkey, other):
		keyfilename = self.keypath + self.prefix + other + ".pub"
		with open(keyfilename, "wb") as fpub:
			fpub.write(strkey)
		self.receiver_keys[other] = RSA.importKey(strkey)
		return True

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
