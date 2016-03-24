#!/usr/bin/env python3

import sys
import random
import socket
import select
import threading
import re

from .security import Security
from .utils import Utils


ENCODING = "utf-16"
BUFFER_SIZE = 4096
DELAY = 0.1
MAX_CONNECTIONS = 100
MSG_END = 5 * chr(0)


class Connection:
	"""Base Connection class"""

	def __init__(self, sock):
		self.buffer = ""
		self.sock = sock

	def send(self, dest, message):
		try:
			dest.sendall(bytes("{}{}".format(message, MSG_END), ENCODING))
		except Exception as e:
			print(e)

	def receive(self, dest):
		try:
			data = dest.recv(BUFFER_SIZE)
			data = str(data)
			if self.buffer:
				data = self.buffer + data
				self.buffer = ""
			end_found = data.find(MSG_END)
			if end_found != -1:
				if len(data) > end_found + len(end_found):
					self.buffer = data[end_found+len(end_found):]
				return data[:end_found]
			else:
				self.buffer += data
		except Exception as e:
			print(e)


class ServerConnection(Connection):
	"""For server connection and transmission of data"""

	input_list = []
	channels = {}
	usernames = {}
	usernames_reverse = {} # useful for reverse lookup
	rx_pubkeys = {}
	
	def __init__(self, host, port = 9876, secure = True, keylength = 4096):
		self.host = host
		self.port = int(port)
		if secure:
			self.sec = Security("Server", keylength, True)
			if self.sec.my_key_pair_exists():
				self.sec.load_my_privkey()
				self.sec.load_my_pubkey()
			else:
				self.sec.create_key_pair()
		else:
			self.sec = None
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.port))
		self.server.listen(MAX_CONNECTIONS)
		super().__init__(self.server)

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
					self.data = self.receive(ready_server)
					#self.data = ready_server.recv(BUFFER_SIZE)
					if self.data:
						self.on_recv(ready_server)
#					else:
#						self.on_close(ready_server)
#						break
			except ConnectionRefusedError:
				print("Client has disconnected!")
			except Exception as e:
				print(e)
				break

	def generate_guestname(self):
		random.seed()
		return "Guest{}".format(random.randrange(100000, 1000000))

	def server_parse_recv_command(self, dest, line):
		line = line.strip()
		l_line = line.lower()

		if l_line.startswith("/setname ") or l_line.startswith("/setname\t"):
			# /setname command
			name = line[9:].lstrip()
			if name not in self.usernames and dest in self.usernames_reverse:
				# client attempting to change name
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				old_name = self.usernames_reverse[dest]
				del self.usernames[old_name]
				self.send(dest, "///nameack///{}".format(name))
				#dest.sendall(bytes("///nameack///{}".format(name), ENCODING))
				print("Client {} changed name to '{}'.".format(self.channels[dest], name))

			elif name not in self.usernames:
				# client choosing name upon connect
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				self.send(dest, "///nameack///{}".format(name))
				#dest.sendall(bytes("///nameack///{}".format(name), ENCODING))
				print("Client {} has identified as '{}'.".format(self.channels[dest], name))

			elif dest not in self.usernames_reverse:
				# name already taken, but generate guest name
				name = self.generate_guestname()
				self.usernames[name] = dest
				self.usernames_reverse[dest] = name
				self.send(dest, "///nameguest///{}".format(name))
				#dest.sendall(bytes("///nameguest///{}".format(name), ENCODING))
				print("Client {} force-changed name to '{}'.".format(self.channels[dest], name))

			else:
				# name already taken
				self.send(dest, "///namedenied///{}".format(name))
				#dest.sendall(bytes("///namedenied///{}".format(name), ENCODING))

		elif l_line == "///list///":
			output = "List of online users:"
			for user in self.usernames:
				output += "\n" + user
			self.send(dest, output)
			#dest.sendall(bytes(output, ENCODING))

		elif l_line.startswith("///listpattern///"):
			line = "^" + line[17:].replace("*", ".*") + "$"
			output = "List of matched online users:"
			for user in self.usernames:
				if re.match(line, user, re.IGNORECASE):
					output += "\n" + user
			self.send(dest, output)
			#dest.sendall(bytes(output, ENCODING))

		elif l_line.startswith("///chat///"):
			# for chat window
			parts = Utils.split(line, "///", 3)
			if parts[1] in self.usernames:
				self.send(self.usernames[parts[1]], "///chat///{}///{}".format(
					self.usernames_reverse[dest], parts[2]))
				#self.usernames[parts[1]].sendall(bytes("///chat///{}///{}".format(
				#	self.usernames_reverse[dest], parts[2]), ENCODING))
			else:
				self.send(dest, "///usernone///{}".format(parts[1]))
				#dest.sendall(bytes("///usernone///{}".format(parts[1]), ENCODING))

		elif l_line.startswith("///schat///"):
			# for chat window when client is using secure comm
			parts = Utils.split(line, "///", 3)
			if parts[1] in self.usernames:
				dec_msg = self.sec.decrypt(parts[2])
				enc_msg = self.sec.encrypt(parts[1], dec_msg)
				self.send(self.usernames[parts[1]], "///schat///{}///{}".format(
					self.usernames_reverse[dest], enc_msg))
				#self.usernames[parts[1]].sendall(bytes("///schat///{}///{}".format(
				#	self.usernames_reverse[dest], enc_msg), ENCODING))
			else:
				self.send(dest, "///usernone///{}".format(parts[1]))
				#dest.sendall(bytes("///usernone///{}".format(parts[1]), ENCODING))

		elif l_line.startswith("///pubkey///"):
			# receiving client pubkey
			parts = Utils.split(line, "///", 2)
			rx_name = self.usernames_reverse[dest]
			if not self.sec.save_other_pubkey(parts[1], rx_name):
				print("Error: could not store remote public key.")
			self.send(dest, "///serverpubkey///{}".format(str(self.sec.pubkey.exportKey())))
			#dest.sendall(bytes("///serverpubkey///{}".format(str(self.sec.pubkey.exportKey())), ENCODING))

		elif l_line.startswith("/"):
			# unrecognized command
			self.send(dest, "///error///unrecognized command.")
			#dest.sendall(bytes("///error///unrecognized command.", ENCODING))

		else:
			# not a command
			print("{}{}".format(self.prompt(self.usernames_reverse[dest], self.channels[dest][0]), line))

	def on_accept(self):
		client_sock, client_addr = self.server.accept()
		self.input_list.append(client_sock)
		self.channels[client_sock] = client_addr
		print("Client {} has connected.".format(client_addr))
		self.send(client_sock, "Welcome.")
		#client_sock.sendall(bytes("Welcome.", ENCODING))

	def on_recv(self, dest):
		self.data = self.data.decode(ENCODING)
		self.server_parse_recv_command(dest, self.data)

	def on_close(self, dest):
		print("Client {} has disconnected.".format(dest.getpeername()))
		name = self.usernames_reverse[dest]
		del self.usernames_reverse[dest]
		del self.usernames[name]
		self.input_list.remove(dest)
		del self.channels[dest]
		dest.close()

	def start_server(self):
		try:
			self.listening_loop()
		except KeyboardInterrupt:
			print("\nStopping server...")
			self.server.close()
			sys.exit(0)

	def prompt(self, name, addr):
		return "[{}@{}]> ".format(name, addr)


class ClientConnection(Connection):
	"""Class for client connection"""

	input_list = []
	rx_pubkeys = {}
	
	def __init__(self, host, port = 9876, username = 'me', secure = True, keylength = 4096):
		self.listen_loop = True
		self.connect_loop = True
		self.host = host
		self.port = int(port)
		self.username = username

		if secure:
			self.sec = Security(self.username, keylength, False)
			if self.sec.my_key_pair_exists():
				self.sec.load_my_privkey()
				self.sec.load_my_pubkey()
			else:
				self.sec.create_key_pair()
		else:
			self.sec = None

		self.mode = ["", ""] # the first is the mode ("", "chat", "shell" or "file") and the second is the target
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket
		self.input_list.append(self.sock)
		super().__init__(self.sock)

	def listen_receive(self):
		readlist, writelist, exceptlist = select.select(self.input_list, [], [], DELAY)
		while self.listen_loop:
			if not self.sock:
				break
			for input_ready in readlist:
				if input_ready == self.sock:
					self.data = self.receive(self.sock)
					#self.data = self.sock.recv(BUFFER_SIZE)
					if self.data:
						self.client_parse_recv_command(self.data.decode(ENCODING))

	def send_name(self):
		self.send(self.sock, "/setname {}".format(self.username))
		#self.sock.sendall(bytes("/setname {}".format(self.username), ENCODING))

	def send_pubkey(self):
		self.send(self.sock, "///pubkey///{}".format(str(self.sec.pubkey.exportKey())))
		#self.sock.sendall(bytes("///pubkey///{}".format(str(self.sec.pubkey.exportKey())), ENCODING))

	def prompt(self, name = ''):
		if not name:
			name = self.username
		return str(name) + "> "

	def client_parse_recv_command(self, line):
		line = line.strip()
		l_line = line.lower()

		if l_line.startswith("///error///"):
			print("Error: {}".format(line[11:]))

		elif l_line.startswith("///nameack///"):
			self.username = line[13:]
			print("{}Your name was set to '{}'.".format(self.prompt("Client"), self.username))

		elif l_line.startswith("///nameguest///"):
			self.username = line[15:]
			print("{}Your name was changed to '{}'.".format(self.prompt("Client"), self.username))

		elif l_line.startswith("///namedenied///"):
			print("{}Name already in use.".format(self.prompt("Server")))

		elif l_line.startswith("///chat///"):
			parts = Utils.split(line, "///", 3)
			print("{}{}".format(self.prompt(parts[1]), parts[2]))

		elif l_line.startswith("///schat///"):
			parts = Utils.split(line, "///", 3)
			print("{}{}".format(self.prompt(parts[1]), self.sec.decrypt(parts[2])))

		elif l_line.startswith("///usernone///"):
			print("{}User '{}' is not online.".format(self.prompt("Server"), line[15:]))

		elif l_line.startswith("///pubkey///"):
			parts = Utils.split(line, "///", 3)
			if not self.sec.save_other_pubkey(parts[2], parts[1]):
				print("Error: could not store remote public key.")

		elif l_line.startswith("///serverpubkey///"):
			parts = Utils.split(line, "///", 2)
			if not self.sec.save_other_pubkey(parts[1], "Server"):
				print("Error: could not store remote public key.")

		elif line:
			print("{}{}".format(self.prompt("Server"), line))

	def client_parse_sent_command(self, sock, line):
		line = line.strip()
		l_line = line.lower()

		if l_line == "/exit" or l_line == "/quit":
			self.connect_loop = False

		elif l_line == "/list":
			line = "///list///"

		elif l_line.startswith("/list ") or l_line.startswith("/list\t"):
			args = line[6:].lstrip()
			line = "///listpattern///{}".format(args)

		elif l_line.startswith("/chat ") or l_line.startswith("/chat\t"):
			args = line[6:].lstrip()
			self.mode = ["chat", args]
			line = ""

		elif l_line.startswith("///chat///") and self.sec:
			parts = Utils.split(line, "///", 3)
			line = "///schat///{}///{}".format(parts[1], self.sec.encrypt("Server", parts[2]))

		elif l_line.startswith("/shell ") or l_line.startswith("/shell\t"):
			args = line[7:].lstrip()
			pass

		elif l_line.startswith("/send ") or l_line.startswith("/send\t"):
			args = line[6:].lstrip()
			pass

		elif l_line == "/close":
			# close chat, shell or file sending
			self.mode = ["", ""]
			line = ""

		if line and self.connect_loop:
			if self.mode[0] == "chat" and not line.startswith("///"):
				appended_line = "///chat///{}///".format(self.mode[1]) + line
			else:
				appended_line = line
			self.send(sock, appended_line)
			#sock.sendall(bytes(appended_line, ENCODING))

	def connect_to_server(self):
		try:
			print(self.prompt("Client") + "Starting...")
			self.sock.connect((self.host, self.port))
			self.listening_thread = threading.Thread(target=self.listen_receive)
			self.listening_thread.daemon = True
			self.listening_thread.start()
			print("{}Connected to server.".format(self.prompt("Client")))
			self.send_name()
			if self.sec:
				self.send_pubkey()

			while self.connect_loop:
				if not self.sock:
					print(self.prompt("Client") + "Server disconnected.")
					break
				line = input()
				self.client_parse_sent_command(self.sock, line)

			print(self.prompt("Client") + "Disconnecting...")
			self.sock.close()
			self.listen_loop = False
			sys.exit(0)

		except ConnectionRefusedError:
			print(self.prompt("Client") + "Error: Assist-Server not available on this address and/or port!")
			self.listen_loop = False
			sys.exit(1)

		except KeyboardInterrupt:
			print("\n" + self.prompt("Client") + "Exiting...")
			self.sock.close()
			self.listen_loop = False
			sys.exit(0)

		except BrokenPipeError:
			print("{}Server closed the connection.".format(self.prompt("Client")))
			self.listen_loop = False
			sys.exit(1)

		except Exception as e:
			self.listen_loop = False
			print(e)
			sys.exit(1)
