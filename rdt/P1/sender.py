import socket
import sys
import time
from PASender import PASender
import logHandler
if __name__=='__main__':
    buf = 1200
    if len(sys.argv) != 5:
        print("Insufficient arguments")
        sys.exit()
    recv_ip = sys.argv[1]
    window_s = sys.argv[2]
    src = sys.argv[3]
    log_file = sys.argv[4]

    logfun = logHandler.logHandler()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    f = open(src,'rb')
    data = f.read(buf)
    sender = PASender(soc=sock, config_file="config.txt")
    logfun.startLogging(log_file)
    sender.sendto(data, (recv_ip, 10090)) 
    logfun.writePkt(0,logfun.SEND_DATA)

    logfun.writeEnd()

    sock.close()
    f.close()