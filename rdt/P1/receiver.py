import socket
import sys

if __name__=='__main__':
    if len(sys.argv) != 3:
        print("Insufficient arguments")
        sys.exit()
        
    result_file = sys.argv[1]
    log_file = sys.argv[2]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('',10090))

    data, addr = sock.recvfrom(1200)
    f = open(result_file,'wb')
    f.write(data)
    sock.close()
    f.close()
