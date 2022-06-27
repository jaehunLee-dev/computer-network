from datetime import datetime
from socket import *
import os
import threading
import sys

user_id = ''
cookie_time = {}

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind(('', 10090))
serverSocket.listen(80)

def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Cannot Create Directory : ' +  directory)

def service(webSocket):                        
    while True:
        fn_from_client = ''                
        global user_id    
        global cookie_time
        file_list = []
        id_idx = -1
        senddata = ''
        time_gap = 120            
        message = webSocket.recv(65535) 

        user_id = ''
        if (message == b''):
            return
            #continue
        filename = message.split()[1]
        message_org=''
        if filename.decode() == '/favicon.ico':
            print('favicon is coming...')            
            continue
        if (filename.decode() != '/favicon.ico'): 
 
            del file_list[0:]
            content_type = message.find(b'multipart')
            cookie_msg = ''            
            if content_type == -1:         #check if it is not multipart data, it is cookie or index or login to storage(first access)                
                id_idx = message.decode().find('id=')           #if it is not login step, id_idx is -1
                pw_idx = message.decode().find('&pw=')
                if (id_idx != -1):                                  #login 단계                    
                    user_id = message.decode()[id_idx+3:pw_idx]         
                    cookie_msg = '\r\nSet-Cookie: ckd='+user_id+'; max-age=120;'        #set new cookie only when it is login step
                    cookie_time[user_id] = datetime.now()
                else:                                               #로그인 아니고, 파일 들어오는 단계 아닐 시 cookie로 얻어오기
                    user_idx = message.decode().find('ckd=')                                          #save cookie to user_id
                    user_idx2 = message.decode().find('\r\n',user_idx)
                    if user_idx != -1:               #there is cookie info
                        user_id = message.decode()[user_idx+4:user_idx2]                        
                
                
            else:                                               #it is multipart data, then save filename and file    파일 들어왔을때                                               
                filename_idx_start = message.find(b'filename=') + 10
                filename_idx_end = message.find(b'"\r\nContent-Type')
                if filename_idx_end != -1:
                    fn_from_client = message[filename_idx_start:filename_idx_end].decode()    
                                                                
                header_idx = message.find(b'\r\n\r\n')
                message_no_header = message[header_idx+4:]                                
                message_header = message[:header_idx+4]
                user_idx = message_header.decode().find('ckd=')                                          #save cookie to user_id
                user_idx2 = message_header.decode().find('\r\n',user_idx)
                
                
                
                if user_idx != -1:               #there is cookie info      쿠키 정보있을때
                    user_id = message_header.decode()[user_idx+4:user_idx2]                    

                else:                              #쿠키 정보 없을때
                    while True:
                        if message[len(message)-4:len(message)] == b'--\r\n':                         
                            break 
                        message = webSocket.recv(66535)
                    
                    f = open('./403err.html', 'rt', encoding='utf-8')                    
                    outputdata = f.read()
                    sendingData = 'HTTP/1.1 200 OK'+'\r\nContent-Length: '+str(len(outputdata))+'\r\n\r\n' + outputdata                    
                    webSocket.send(sendingData.encode('utf-8'))                                                                          
                    continue 
                
                if filename_idx_end != -1 and user_idx != -1:
                    write_file = open(os.getcwd()+"/"+user_id + "/"+fn_from_client , "wb")                    
                
                message = message_no_header
                message_org = message_no_header                
                i = 1
                while True:                     
                    if message_org[len(message_org)-4:len(message_org)] != b'--\r\n':  #한번에 다들어온게 아닌 케이스에서는, 남은 데이터들 받기.                        
                        message = webSocket.recv(65535)
                        message_no_header = message_no_header + message         #combine all messages
                    if i==1:
                        i+=1
                        if message.find(b'filename') != -1:                        
                            filename_idx_start = message.find(b'filename=') + 10
                            filename_idx_end = message.find(b'"\r\nContent-Type')
                            fn_from_client = message[filename_idx_start:filename_idx_end].decode()      #filename 추출                            
                            write_file = open(os.getcwd()+"/"+user_id + "/"+fn_from_client , "wb")     
                        
                    if i==2:
                        webkit_idx_end = message_no_header.find(b'\r\n\r\n') + 4
                        webkit_msg = message_no_header[:webkit_idx_end]             #find webkit msg
                        webkit_submsg = webkit_msg[0:webkit_msg.find(b'\r\nContent')]                        
                        i+=1
                    
                    if message[len(message)-4:len(message)] == b'--\r\n':                         
                        break                                                                                         
                
                #remove webkit messages (3 cases)
                message_no_header = message_no_header[webkit_idx_end:]
                                
                webkit_endmsg_idx = message_no_header.rfind(b'\r\n------WebKit')
                message_no_header = message_no_header[:webkit_endmsg_idx]
                webkit_endmsg_idx = message_no_header.rfind(b'\r\n------WebKit')
                message_no_header = message_no_header[:webkit_endmsg_idx]                                                                         
                while message_no_header.find(webkit_submsg) != -1:                
                    message_no_header = message_no_header[:message_no_header.find(webkit_submsg)] + message_no_header[message_no_header.find(webkit_submsg)+len(webkit_submsg):]
                write_file.write(message_no_header)                                                                                                                                                                                                                                                                                                                                                                                                                     
                                                                                            
            
            if (filename.decode() == '/' or filename.decode() == '/index.html'):
                f = open('./index.html' , 'rt', encoding='utf-8')
                
            elif filename.decode().find('/storage.html') != -1 or filename.decode().find('delete') != -1 or filename.decode().find('down') != -1:
                if filename.decode().find('/storage.html') == -1:       #파일 업로드/딜리트 할 때
                    if user_id == '':
                        f = open('./403err.html', 'rt', encoding='utf-8')
                        outputdata = f.read()
                        sendingData = 'HTTP/1.1 200 OK'+'\r\nContent-Length: '+str(len(outputdata))+'\r\n\r\n' + outputdata
                        webSocket.send(sendingData.encode('utf-8'))
                        continue                    
                if filename.decode().find('delete') != -1:
                    del_file_idx = filename.decode().rfind('/')
                    del_file = filename.decode()[del_file_idx+1:]
                    (del_file)                    
                    os.remove(os.getcwd()+"/"+user_id + "/"+del_file)
                elif filename.decode().find('down') != -1:                
                    down_file_idx = filename.decode().rfind('/')
                    down_file = filename.decode()[down_file_idx+1:]
                    #file 전송 여기서 하기.
                    sendfile = open(user_id+'/'+down_file,"rb")
                    senddata = sendfile.read()
                    sendfile.close()
                    senddata = b'HTTP/1.1 200 OK\r\nContent-Disposition: attachment\r\nContent-Length: '+bytes(str(len(senddata)),encoding='utf8') + b'\r\n\r\n' + senddata
                    webSocket.send(senddata)                                                                                                            
                                    
                if (user_id == '' and content_type == -1):             #there is no account info, then go  to 403 page |||||||          content-type이 -1이면 file이 들어오지 않은것
                    f = open('./403err.html', 'rt', encoding='utf-8')
                else:                               #파일이 들어왔거나, user_id 정보가 로그인/쿠키로 인해 있는 경우
                    f = open('./storage.html', 'rt', encoding='utf-8')          #cookie 또는 바로 로그인 해서 user 정보가 있을 때                    
                    createFolder(user_id)
                    file_list = os.listdir(user_id)                
                    file_list.reverse()                    
                
            elif filename.decode() == '/cookie.html':
                if user_id == '':
                    f = open('./403err.html', 'rt', encoding='utf-8')
                else :
                    f = open('./cookie.html', 'rt', encoding='utf-8')
                    time_gap = (datetime.now() - cookie_time[user_id]).seconds
                    time_gap = 120 - time_gap                    
                
            else:
                print("error")                                
            
            outputdata = f.read()
            outputdata = outputdata.replace('timeleft', str(time_gap))

                                
            #f.close()            
            
            outputdata = outputdata.replace('user1', user_id)
            file_list_idx = outputdata.find('</ul>')
            for i in file_list:
                outputdata = outputdata[:file_list_idx] + '<li>'+i+'<a href="/down/'+i+'" ><button>Download</button></a>_' +'<a href="/delete/'+i+'"><button>Delete</button></a>'+'</li>' + outputdata[file_list_idx:]            
            if senddata == '':              #클라이언트에서의 파일 다운로드가 아닐 때
                sendingData = 'HTTP/1.1 200 OK'+cookie_msg+'\r\nContent-Length: '+str(len(outputdata))+'\r\n\r\n' + outputdata
                webSocket.send(sendingData.encode('utf-8'))

            print("OK!")


    

while True:    
    webSocket, addr = serverSocket.accept()    

    q = threading.Thread(target=service,args=(webSocket,))
    q.start()    
    
    
serverSocket.close()