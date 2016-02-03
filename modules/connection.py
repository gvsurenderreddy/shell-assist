#!/usr/bin/env python

import sys
import socket
import select


class ForwardServer:
	"""Forward-proxy server"""
	def __init__(self, host, port):
		self.host = host
		self.port = int(port)
		self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def start_server(self):
		try:
			self.forward.connect((self.host, self.port))
			return self.forward
		except Exception as e:
			print(e)
			return False


class ServerConnection:
	"""For server connection and transmission of data"""

	BUFFER_SIZE = 4096
	DELAY = 0.001
	MAX_CONNECTIONS = 100
	input_list = []
	channels = {}
	
	def __init__(self, host, port = 9876):
		self.host = host
		self.port = int(port)
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.port))
		self.server.listen(self.MAX_CONNECTIONS)

	def listening_loop(self):
		print("Listening to connections...")
		self.input_list.append(self.server)
		while True:
			try:
				readlist, writelist, exceptlist = select.select(self.input_list, [], [], self.DELAY)
			except Exception as e:
				print(e)
				break
			for ready_server in readlist:
				if ready_server == self.server:
					self.on_accept()
					break
				self.data = ready_server.recv(self.BUFFER_SIZE)
				if len(self.data):
					self.on_recv(ready_server)
				else:
					self.on_close(ready_server)
					break

	def on_accept(self):
		#forward_sock = ForwardServer(self.host, self.port).start_server()
		client_sock, client_addr = self.server.accept()
		self.input_list.append(client_sock)
		self.channels[client_sock] = client_addr
		print("{} has connected.".format(client_addr))
		# if forward_sock:
		# 	print("{} has connected.".format(client_addr))
		# 	self.input_list.append(client_sock)
		# 	self.input_list.append(forward_sock)
		# 	self.channels[client_sock] = forward_sock
		# 	self.channels[forward_sock] = client_sock
		# else:
		# 	print("Could not establish connection with server.")
		# 	print("Closing connection with client {}.".format(client_addr))
		# 	client_sock.close()


	def on_recv(self, dest):
		print("Received from {}:\n{}".format(dest, self.data))
		self.channels[dest].sendall(self.data)

	def on_close(self, dest):
		print("{} has disconnected.".format(dest.getpeername()))
		self.input_list.remove(dest)
		#self.input_list.remove(self.channels[dest])
		#self.channels[dest].close()
		#del self.channels[self.channels[out]]
		del self.channels[dest]
		dest.close()

	def start_server(self):
		try:
			self.listening_loop()
		except KeyboardInterrupt:
			print("\nStopping server...")
			self.server.close()
			sys.exit(0)


class ClientConnection:
	"""For client connection"""
	
	def __init__(self, host, port = 9876, username = 'me'):
		self.host = host
		self.port = int(port)
		self.username = username
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket

	def connect_to_server(self):
		try:
			self.sock.connect((self.host, self.port))
			line = input(str(self.username) + "> ")
			while line.lower() != "exit":
				self.sock.sendall(bytes(line))
				line = input(str(self.username) + "> ")
		except KeyboardInterrupt:
			print("\nStopping client...")
			self.sock.close()
			sys.exit(0)
