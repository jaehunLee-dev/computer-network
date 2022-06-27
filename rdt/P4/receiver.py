import socket
import sys
from struct import *
import logHandler

def isCorruption(data, cksum):
    if len(data) %2 != 0:
        data = data + b'\x00'

    data = unpack('!' + 'H' * (len(data)//2), data)
    data = sum(data)

    while True:
        carry = (data & 0xFFFF0000) >> 16
        if carry == 0:
            break
        data = (data & 0xFFFF) + carry

    if data + cksum == 65535:
        return 0        # no corruption
    else:
        return 1        #corruption


if __name__=='__main__':
    print('starting')
    if len(sys.argv) != 3:
        print("Insufficient arguments")
        sys.exit()
    result_file = sys.argv[1]
    log_file2 = sys.argv[2]
    logfun2 = logHandler.logHandler()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('',10090))

    f = open(result_file,'wb')
    prv_ack = b'19'
    logfun2.startLogging(log_file2)
    while True:
        data, addr = sock.recvfrom(2500)
        if data == b'endfinish':
            sock.sendto(b'100', (addr[0],addr[1]))      #send ack for finish
            print('real finished')
            break
        payload_idx = data.find(b'\r\n\r\n') + 4
        chksum_idx = data.find(b'chksum:')+7
        payload = data[payload_idx:]
        seq_idx = data.find(b'seq:') + 4
        seq_idx_end = data.find(b'\r\nchksum')
        seq_num = data[seq_idx:seq_idx_end]
        chksum = data[chksum_idx:payload_idx-4]

        try:
            chksum = int(chksum.decode())
            data = data[:chksum_idx] + b'0' + data[payload_idx-4:]     #set chksum as 0 for header corruption detection
        except: #corrupted header
            sock.sendto(prv_ack, (addr[0],addr[1]))
            logfun2.writeAck(prv_ack.decode(),logfun2.SEND_ACK)
            continue

        if isCorruption(data, chksum) : #corruption -> send most recent ack
            sock.sendto(prv_ack, (addr[0],addr[1]))
            logfun2.writeAck(prv_ack.decode(), logfun2.SEND_ACK)
            
            
        else:                               #no corruption -> save data and send current ack
            if int(seq_num.decode()) != (int(prv_ack.decode())+1)%20:        #패킷로스로 와야하는 패킷 다음 패킷이 온 경우                
                sock.sendto(prv_ack,(addr[0],addr[1]))                
            else:
                if payload.find(b'finpack123') == -1:
                    f.write(payload)                
                prv_ack = seq_num
                sock.sendto(seq_num,(addr[0],addr[1]))
                logfun2.writeAck(prv_ack.decode(), logfun2.SEND_ACK)

    print("received data")
    logfun2.writeEnd()
    sock.close()
    f.close()
    print('end')