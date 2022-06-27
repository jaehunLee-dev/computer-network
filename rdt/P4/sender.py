import socket
import sys
import time
from PASender import PASender
from struct import *
import logHandler
import threading

global end
end = 0

global wd
wd = []     #window for data
global wd_seq
wd_seq = [] #window for seq_num of data
global wd_idx
wd_idx = 0
global seq_num
global front
front = 0       #윈도우의 가장 앞에 있는 seq_num 저장 (0~window_s-1)
global tosendNum
global retransmit
retransmit = 0
global finish

def recv_ack(sock):
    global retransmit
    global front
    global wd_seq
    global tosendNum
    global end
    global wd_idx
    global finish
    
    sock.settimeout(0.01)
    while True:        
        try:                        
            ack, addr = sock.recvfrom(128)        
            if int(ack.decode()) == 100:                
                finish = 1
                break
            if int(ack.decode()) == wd_seq[front]:
                #올바른 ack -> tosendNum 하나 더해주기 + time 멈추기 (send하고 다시 타이머)
                tosendNum+=1                
                front=(front+1)%window_s                
                
                #sock.settimeout(None)   #이거맞나
            else:       #잘못된 ack -> timeout (재설정 후) 기다리기
                continue
        except socket.timeout:      #timeout -> window 재전송
            retransmit = 1
        if end == 1:
            break
    return

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
    window_s = int(window_s)
    src = sys.argv[3]
    log_file = sys.argv[4]
    finish = 0
    logfun = logHandler.logHandler()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    f = open(src,'rb')
    data = f.read(buf)

    seq_num = 0 #seq_num 최대 19까지, 처음 seq_num = 0
    
    sender = PASender(soc=sock, config_file="config.txt")
    logfun.startLogging(log_file)


    tosendNum = int(window_s)    #보내야할 데이터 갯수
    
    t_recv = threading.Thread(target=recv_ack, args=(sock,))
    t_recv.start()      #ack 수신용 쓰레드 실행
#    sock.settimeout(0.01)
    #for i in range(window_s):   #처음에 window만큼 버퍼링 및 전송
    wd = [0 for i in range(window_s)]
    wd_seq = [0 for i in range(window_s)]    
    while True:
        #여기부터
        if finish == 1:
            break
        out = 1
        for i in range(window_s):
            tmpwd = str(wd[i]).encode()
            if (tmpwd).find(b'finpack123') == -1:
                out = 0
                break            
        if out == 1:        #window가 전부 b''이면, 파일 전송 끝 -> b'end' 전송 후 ack 받으면 break하기
            sender.sendto_bytes(b'endfinish',(recv_ip,10090))
            print('파일 전송 완료')            
        #여기까지 수정중

        if end == 1:
            break

        if retransmit == 1: #timeout으로 인한 재전송
            for i in range(window_s):       #window 처음부터 순서대로 전송
                sender.sendto_bytes(wd[(front+i)%window_s], (recv_ip, 10090))
            retransmit = 0
            continue

        if tosendNum <= 0:      #window 다씀 (더 보낼수 없음)
            continue
            
        else:   #윈도우 여유 있으면 읽고 보내기
            if data == b'':
                #여기서부터                                
                data_go = b'seq:'+str(seq_num).encode()+b'\r\nchksum:0' + b'\r\n\r\n' + b'finpack123'    #data with checksum header (for checksum corruption, assume checksum as 0)
                chksum = checksum(data_go)
                data_go = b'seq:'+str(seq_num).encode()+b'\r\nchksum:'+ str(chksum).encode() + b'\r\n\r\n' + b'finpack123'   #set checksum as real value for sending                                        
                data = b''
                wd[wd_idx] = data_go        #데이터를 윈도우(버퍼)에 저장
                wd_seq[wd_idx] = seq_num             #ack 확인을 위한 seq_num 저장
                wd_idx=(wd_idx+1)%window_s                
                sender.sendto_bytes(data_go,(recv_ip,10090))       #빈 데이터 전송, 빈 데이터가 윈도우에 꽉차면 파일전송 완료                
                tosendNum -= 1
                seq_num=(seq_num+1)%20  ####here                                
                continue

            #헤더붙이기
            data_with_header = b'seq:'+str(seq_num).encode()+b'\r\nchksum:0' + b'\r\n\r\n' + data    #data with checksum header (for checksum corruption, assume checksum as 0)
            chksum = checksum(data_with_header)
            data_with_header = b'seq:'+str(seq_num).encode()+b'\r\nchksum:'+ str(chksum).encode() + b'\r\n\r\n' + data   #set checksum as real value for sending        


            wd[wd_idx] = data_with_header        #데이터를 윈도우(버퍼)에 저장
            wd_seq[wd_idx] = seq_num             #ack 확인을 위한 seq_num 저장
            wd_idx=(wd_idx+1)%window_s      #다음 데이터 저장할 idx 설정
            sender.sendto_bytes(data_with_header, (recv_ip, 10090)) #후 전송
            tosendNum -= 1              #하나 보냈으니 보내야할 것 하나 줄이기

            logfun.writePkt(seq_num,logfun.SEND_DATA) 
            data = f.read(buf)          #다음 데이터 읽기
            seq_num=(seq_num+1)%20      #window size가 5~10이므로, seq_num의 범위를 0~19로 지정

    logfun.writeEnd()

    sock.close()
    f.close()