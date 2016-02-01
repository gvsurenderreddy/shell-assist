#!/usr/bin/env python

import socket
from socketserver import TCPServer, BaseRequestHandler


class CustomTCPHandler(BaseRequestHandler):
	"""Overrides BaseRequestHandler class with a custom handler method"""
	
	def handle(self):
		self.server.recv_data = self.request.recv(1024).strip()


class ServerConnection:
	"""For server (forward-proxy) connection and transmission of data"""
	
	def __init__(self, host = "localhost", port = 9876):
		self.host = host
		self.port = port

	def start_server(self):
		try:
			self.server = TCPServer((self.host, self.port), CustomTCPHandler)
			self.server.serve_forever()
		except KeyboardInterrupt:
			print("\nStopping server...")

	def stop_server(self):
		try:
			self.server.shutdown()
			self.server.server_close()
		except:
			print("\nCould not stop server. Perhaps it has already stopped.")


class ClientConnection:
	"""For client connection"""
	
	def __init__(self, host = "localhost", port = 9876):
		self.host = host
		self.port = port
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket

	def connect_to_server(self):
		try:
			self.sock.connect((self.host, self.port))
		finally:
			self.sock.close()
