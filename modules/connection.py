#!/usr/bin/env python

import sys
import socket
import select
import threading


ENCODING = "utf-16"
BUFFER_SIZE = 4096
DELAY = 0.1
MAX_CONNECTIONS = 100


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

	input_list = []
	channels = {}
	usernames = {}
	
	def __init__(self, host, port = 9876):
		self.host = host
		self.port = int(port)
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.port))
		self.server.listen(MAX_CONNECTIONS)

	def listening_loop(self):
		print("Assist-Server starting...")
		print("Listening to connections...")
		self.input_list.append(self.server)
		while True:
			try:
				readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
				for ready_server in readlist:
					if ready_server == self.server:
						self.on_accept()
						break
					self.data = ready_server.recv(BUFFER_SIZE)
					if len(self.data):
						self.on_recv(ready_server)
					else:
						self.on_close(ready_server)
						break
			except ConnectionRefusedError:
				print("Client has disconnected!")
			except Exception as e:
				print(e)
				break

	def on_accept(self):
		#forward_sock = ForwardServer(self.host, self.port).start_server()
		client_sock, client_addr = self.server.accept()
		self.input_list.append(client_sock)
		self.channels[client_sock] = client_addr
		print("Client {} has connected.".format(client_addr))
		client_sock.sendall(bytes("Welcome.", ENCODING))
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
		self.data = self.data.decode(ENCODING)
		if self.data.strip().lower().startswith("/setname "):
			name = self.data.strip()[9:]
			if name not in self.usernames:
				self.usernames[dest] = name
				print("Client {} has identified as '{}'.".format(self.channels[dest], name))
		else:
			print("{}{}".format(self.prompt(self.usernames[dest]), self.data))
			#dest.sendall(self.data)

	def on_close(self, dest):
		print("Client {} has disconnected.".format(dest.getpeername()))
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

	def prompt(self, name):
		return "{}> ".format(name)


class ClientConnection:
	"""For client connection"""

	input_list = []
	
	def __init__(self, host, port = 9876, username = 'me'):
		self.loop = True
		self.host = host
		self.port = int(port)
		self.username = username
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket
		#self.input_list.append(sys.stdin)
		self.input_list.append(self.sock)

	def listen_receive(self):
		readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
		while self.loop:
			if not self.sock:
				break
			for input_ready in readlist:
				if input_ready == self.sock:
					self.data = self.sock.recv(BUFFER_SIZE)
					if self.data:
						print(self.prompt("Server"), self.data.decode(ENCODING))
					else:
						break

	def send_name(self):
		self.sock.sendall(bytes("/setname {}".format(self.username), ENCODING))

	def prompt(self, name = ''):
		if not name:
			name = self.username
		return str(name) + "> "

	def connect_to_server(self):
		try:
			print(self.prompt("Client") + "Starting...")
			self.sock.connect((self.host, self.port))
			self.listening_thread = threading.Thread(target=self.listen_receive)
			self.listening_thread.start()
			print(self.prompt("Client") + "Connected to server.")
			self.send_name()
			while True:
				if not self.sock:
					print(self.prompt("Client") + "Server disconnected.")
					break
				line = input(self.prompt())
				if line.lower().strip() == "/exit":
					break
				if line.strip():
					self.sock.sendall(bytes(line, ENCODING))
			print(self.prompt("Client") + "Disconnecting...")
			self.sock.close()
			self.loop = False
			sys.exit(0)
		except ConnectionRefusedError:
			print(self.prompt("Client") + "Error: Assist-Server not available on this address and/or port!")
			self.loop = False
			sys.exit(1)
		except KeyboardInterrupt:
			print("\n" + self.prompt("Client") + "Exiting...")
			self.sock.close()
			self.loop = False
			sys.exit(0)
		except Exception as e:
			self.loop = False
			print(e)
			sys.exit(1)
