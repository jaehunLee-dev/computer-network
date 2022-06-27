import socket
import sys
import time
from PASender import PASender
from struct import *
import logHandler

def checksum(data):
    if len(data) %2 != 0:
        data = data + b'\x00'

    data = unpack('!' + 'H' * (len(data)//2), data)
    data = sum(data)

    while True:
        carry = (data & 0xFFFF0000) >> 16
        if carry == 0:
            break
        data = (data & 0xFFFF) + carry
    
    data = data ^ 0xFFFF

    return data
if __name__=='__main__':
    buf = 1024
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

    seq_num = 0

    sender = PASender(soc=sock, config_file="config.txt")
    logfun.startLogging(log_file)
    while True:
        
        if data == b'':         #파일 전송이 끝났음
            finished_send = 0
            while True:
                sender.sendto_bytes(data, (recv_ip, 10090))
                if finished_send == 0:
                    logfun.writePkt(seq_num,logfun.SEND_DATA)
                    finished_send+=1
                else:
                    logfun.writePkt(seq_num,logfun.SEND_DATA_AGAIN)

                sock.settimeout(0.01)
                try:
                    ack_end, addr = sock.recvfrom(128)
                    logfun.writePkt(seq_num,logfun.SUCCESS_ACK)
                    break
                except socket.timeout:
                    logfun.writeTimeout(seq_num)
                    continue
            break
        else: 
            data_with_header = b'seq:'+str(seq_num).encode()+b'\r\nchksum:0' + b'\r\n\r\n' + data    #data with checksum header (for checksum corruption, assume checksum as 0)
            chksum = checksum(data_with_header)
            data_with_header = b'seq:'+str(seq_num).encode()+b'\r\nchksum:'+ str(chksum).encode() + b'\r\n\r\n' + data   #set checksum as real value for sending        
            sender.sendto_bytes(data_with_header, (recv_ip, 10090))
            logfun.writePkt(seq_num,logfun.SEND_DATA)
            sock.settimeout(0.01)       #전송 후 timeout 설정
        while True:
            try:
                ack, addr = sock.recvfrom(128)
                if ack != str(seq_num).encode():        #잘못된 ack -> 무시
                    logfun.writePkt(seq_num,logfun.WRONG_SEQ_NUM)
                    continue
                
                sock.settimeout(None)
                #ack 제대로 받았을 때 -> 다음꺼 전송
                logfun.writePkt(seq_num,logfun.SUCCESS_ACK)
                data = f.read(buf)
                seq_num = 1 - seq_num
                break
            except socket.timeout:                        #timeout -> 재전송
                logfun.writeTimeout(seq_num)                #timeout 기록
                sender.sendto_bytes(data_with_header, (recv_ip, 10090)) #재전송
                logfun.writePkt(seq_num,logfun.SEND_DATA_AGAIN)                        

    logfun.writeEnd()

    sock.close()
    f.close()