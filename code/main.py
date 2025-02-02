#!/usr/bin/python3
import asyncio
import getopt

import aiomas
import logging
import sys
from Node import Node
from ipc import ApiServer
from helpers.iniParser import IniParser
from helpers.openssl import *

"""
Main application
"""

# Parse console arguments
opts, args = getopt.getopt(sys.argv[1:], "I:i:B:b:c:h:")

# Try to load config.ini from parameters
configname = None

for key, val in opts:
    if key == "-c" :
        configname = val

logfile = None
hostkey = None
nodeIdentifier = None
ipaddress = "localhost"
apiport = None
bootip = bootport = None
kx_port = 0
if configname:
    projectIni = IniParser(configname)
    ipaddress = projectIni.get("HOSTNAME", "DHT")
    port = int(projectIni.get("PORT", ""))
    apiport = int(projectIni.get("PORT", "DHT"))

    bootip = projectIni.get("OVERLAY_HOSTNAME", "DHT")
    bootport = projectIni.get("PORT", "BOOTSTRAP")
    hostkey = projectIni.get("HOSTKEY", "")

    kx_port = int(projectIni.get("PORT", "KX"))

    logfile = projectIni.get("LOG")

if logfile:
    logging.basicConfig(filename=logfile, format='[%(levelname)s:%(funcName)s] %(message)s', level=logging.INFO)
else:
    logging.basicConfig(format='[%(levelname)s:%(funcName)s] %(message)s', level=logging.INFO)

# Overwrite config definitions with params given by CLI
for key, val in opts:
    if key == "-I":
        ipaddress = val
    if key == "-i":
        port = int(val)
    if key == "-B":
        bootip = val
    elif key == "-b":
        bootport = int(val)
    elif key == "-h":
        hostkey = val

if hostkey is not None and hostkey != "":
    nodeIdentifier = makeSha256FromPem(hostkey)
else:
    print("WARNING: Hostkey is None")

print("-------------------")

if apiport is None:
    apiport = port + 3086

# Testing: First port is bootstrap node
bootstrap_addr = ("tcp://"+bootip+":" + str(bootport) + "/0") if bootip else None
print("Address/Port of Bootstrap Node: ", (bootstrap_addr or "this node"))
print("Port", port)
print("-------------------")
print("Bootstrap PORT", bootport)
print("Boostrap IP", bootip)
print("Hostkey", hostkey)
print("Node ID", nodeIdentifier)
print("API PORT", apiport)
print("KX PORT", kx_port)
print("-------------------")
time.sleep(3)

# Define multiple agents per node for accepting RPCs
c = aiomas.Container.create((ipaddress, port))
intitiator = InitiatorAgent(container)
nodes = [Node(c) for i in range(2)]

loop = asyncio.get_event_loop()
# Start API server interface
api_server = loop.create_server(lambda: ApiServer(nodes[0]), ipaddress, apiport)
loop.run_until_complete(api_server)
# Start DHT node
loop.run_until_complete(nodes[0].join(bootstrap_address=bootstrap_addr, node_id=nodeIdentifier, additional_data={"kx_port": kx_port}))
loop.run_until_complete(nodes[0].stabilize())

# Test RPC calls within the same node from backup agent 1 to agent 0
#loop.run_until_complete(nodes[1].test_get_node_id(nodes[0].addr))

# Test RPC calls to bootstrap node (first port)
#if bootstrap_addr:
#    loop.run_until_complete(nodes[0].test_get_node_id(bootstrap_addr))
    #loop.run_until_complete(nodes[0].test_get_closest_preceding_finger(bootstrap_addr, 123))
    #loop.run_until_complete(nodes[0].test_find_my_successor(bootstrap_addr))

loop.run_forever()
c.shutdown()
