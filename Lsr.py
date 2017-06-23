#!/usr/local/bin/python3.5 -u
from socket import *
from sys import *
from threading import *
from collections import *
from operator import *

#for generating least cost path
def least_cost():
    global Node_Name
    global ROUTE_UPDATE_INTERVAL
    global routing
    check = []
    fpp = {}
    fpl = {}
    fpp[Node_Name] = [Node_Name]
    fpl[Node_Name] = 0
    cur = Node_Name
    while len(check) != len(routing):
        check.append(cur)
        for i in routing[cur]:
            if i in check:
                continue
            if i not in fpp:
                fpp[i] = fpp[cur].copy()
                fpp[i].append(i)
                fpl[i] = fpl[cur] + routing[cur][i]
            if i in fpp:
                com = fpl[i] - (fpl[cur] + routing[cur][i])
                if com > 0:
                    fpp[i] = fpp[cur].copy()
                    fpp[i].append(i)
                    fpl[i] = fpl[cur] + routing[cur][i]
        sorted_d = sorted(fpl.items(), key=lambda kv: (kv[1], kv[0]))
        for i in sorted_d:
            if i[0] not in check:
                cur = i[0]
                break
    print()
    for i in sorted(fpl):
        if i == Node_Name:
            continue
        path = ''.join(fpp[i])
        print("least-cost path to node {}: {} and the cost is {}".format(i, path, fpl[i]))
    print()
    global t2
    t2.cancel()
    t2 = Timer(ROUTE_UPDATE_INTERVAL, least_cost, None)
    t2.start()

#check neighbour node failures and update the link state
def check_node_loss():
    global neighbour
    global nei_check
    global link_state
    global Node_Name
    global routing
    if len(nei_check) < len(neighbour):
        remove_list = []
        for i in neighbour:
            if i not in nei_check:
                remove_list.append(i)
        for i in remove_list:
            neighbour.pop(i, None)
        link_state = Node_Name + '\n'
        for i in neighbour:
            link_state += i + '-' + neighbour[i]['cost'] + ' '
        link_state = link_state.rstrip(' ')
        link_state += '\n' + Node_Name
        for i in neighbour:
            link_state += ' ' + i
        for i in remove_list:
            routing[Node_Name].pop(i, None)
            routing[i].pop(Node_Name, None)
            if len(routing[i]) == 0:
                routing.pop(i, None)
    nei_check.clear()
    
#send link state to neighbour
def send_link_state(socket, sevname):
    global UPDATE_INTERVAL
    global neighbour
    global HEARTBEAT
    global HB_count
    global link_state
    if HB_count == HEARTBEAT:
        HB_count = 0
        HEARTBEAT = 3
        check_node_loss()
    try:
        for i in neighbour:
            socket.sendto(link_state.encode('utf-8'), (sevname, neighbour[i]['port']))
    except RuntimeError:
        for i in neighbour:
            socket.sendto(link_state.encode('utf-8'), (sevname, neighbour[i]['port']))
    HB_count += 1
    global t
    t.cancel()
    t = Timer(UPDATE_INTERVAL, send_link_state, (socket, sevname))
    t.start()

#get argv value and set the serverPort and Name
Node_Name = argv[1]
serverPort = int(argv[2])
serverName = '127.0.0.1'
file = open(argv[3], 'r')
line = file.readline()

#dictionary for storing neighbour, routing
neighbour = {}
routing = {}

#check the receive meesage, and check the neighbour
already_rev = []
nei_check = {}

#some constant values, the HEARTBEAT will change to 3 later
ROUTE_UPDATE_INTERVAL = 30
UPDATE_INTERVAL = 1
HEARTBEAT = 10
HB_count = 0

routing[Node_Name] = {}
link_state = Node_Name + '\n'

serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))

#get neighbour from txt file
#also build the routing and link_state message
while line:
    line = file.readline()
    line = line.strip()
    element = line.split()
    if len(element) != 3:
        continue
    neighbour[element[0]] = {}
    neighbour[element[0]]['port'] = int(element[2])
    neighbour[element[0]]['cost'] = element[1]
    link_state += element[0] + '-' + neighbour[element[0]]['cost'] + ' '
    if element[0] not in routing:
        routing[element[0]] = {}
    routing[element[0]][Node_Name] = float(element[1])
    routing[Node_Name][element[0]] = float(element[1])
link_state = link_state.rstrip(' ')
link_state += '\n' + Node_Name
for i in neighbour:
    link_state += ' ' + i

#two timer, t for sending link state, t2 for generating path
t = Timer(UPDATE_INTERVAL, send_link_state, (serverSocket, serverName))
t.start()
t2 = Timer(ROUTE_UPDATE_INTERVAL, least_cost, None)
t2.start()

#get link state message from other nodes, update the routing
#and send to other nodes
while 1:
    message, clientAddress = serverSocket.recvfrom(2048)
    message = message.decode('utf-8')
    mes_sp = message.split('\n')
    nei_list = {}
    if mes_sp[0] in neighbour:
        nei_check[mes_sp[0]] = 1
    temp = mes_sp[1].split(' ')
    for i in temp:
        element = i.split('-')
        if len(element) != 2:
            continue
        nei_list[element[0]] = 1
    if mes_sp[0] not in already_rev:
        for i in temp:
            element = i.split('-')
            if len(element) != 2:
                continue
            if mes_sp[0] not in routing:
                routing[mes_sp[0]] = {}
            if element[0] not in routing:
                routing[element[0]] = {}
            routing[element[0]][mes_sp[0]] = float(element[1])
            routing[mes_sp[0]][element[0]] = float(element[1])
    else:
        already_rev.append(mes_sp[0])
    if len(routing[mes_sp[0]]) > len(nei_list):
        remove_list = []
        for i in routing[mes_sp[0]]:
            if i not in nei_list:
                remove_list.append(i)
        for i in remove_list:
            routing[mes_sp[0]].pop(i, None)
            routing[i].pop(mes_sp[0], None)
            if len(routing[i]) == 0:
                routing.pop(i, None)
    avoid_retransmit = mes_sp[2].split(' ')
    send_list = []
    for i in neighbour:
        if i not in avoid_retransmit:
            send_list.append(i)
            message += ' ' + i
    message = message.encode('utf-8')
    try:
        for i in send_list:
            if i == mes_sp[0]:
                continue
            if i in routing[mes_sp[0]]:
                continue
            serverSocket.sendto(message, (serverName, neighbour[i]['port']))
    except RuntimeError:
        for i in send_list:
            if i == mes_sp[0]:
                continue
            if i in routing[mes_sp[0]]:
                continue
            serverSocket.sendto(message, (serverName, neighbour[i]['port']))
