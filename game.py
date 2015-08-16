#!/usr/bin/env python2
# coding: utf-8

import os,socket,threading,time
#import traceback

allow_delete = False
local_ip = '127.0.0.1'
local_port = 21
currdir=os.path.abspath('.')


class GameItem:
    def __init__(self, name, isDir, isLocked):
        self.name = name
        self.isDir = isDir
        self.isLocked = isLocked
        
    def __str__(self):
        return "GameItem " + self.name
        
class Game:
    def __init__(self,server):
        self.server = server
        self.items = [GameItem("rope-1", False, False), GameItem("rope-2", False, False), GameItem("door", True, True)]
        
    # returns true if (at least?) 1 item was deleted
    def removeItemByName(self, itemName):
        oldItemCount = len(self.items)
        self.items = [o for o in self.items if (o.name != itemName or o.isLocked)]
        itemWasDeleted = len(self.items) < oldItemCount
        return itemWasDeleted
       
# a level (scene?) with ropes
class Level1(Game):
    def __init__(self, server):
        Game.__init__(self, server)
        
    # on this level, the door opens if all ropes are cut
    def removeItemByName(self, itemName):
        retVal = Game.removeItemByName(self, itemName)
        numberOfRopes = len([o for o in self.items if o.name.startswith("rope")])
        if numberOfRopes == 0:
            for x in [o for o in self.items if o.name.startswith("door")]:
                x.name = "door-open"
                x.isLocked = False
        return retVal
    
class FTPserverThread(threading.Thread):
    def __init__(self,(conn,addr)):
        self.conn=conn
        self.addr=addr
        self.cwd = '/'
        self.rest=False
        self.pasv_mode=False
        self.game = Level1(self)
        threading.Thread.__init__(self)

    def run(self):
        self.conn.send('220 Welcome!\r\n')
        while True:
            cmd=self.conn.recv(256)
            if not cmd: break
            else:
                print 'Received:',cmd
                try:
                    func=getattr(self,cmd[:4].strip().upper())
                    func(cmd)
                except Exception,e:
                    print 'ERROR:',e
                    #traceback.print_exc()
                    self.conn.send('500 Sorry.\r\n')

    def SYST(self,cmd):
        self.conn.send('215 UNIX Type: L8\r\n')
    def OPTS(self,cmd):
        if cmd[5:-2].upper()=='UTF8 ON':
            self.conn.send('200 OK.\r\n')
        else:
            self.conn.send('451 Sorry.\r\n')
    def USER(self,cmd):
        self.conn.send('331 OK.\r\n')
    def PASS(self,cmd):
        self.conn.send('230 OK.\r\n')
        #self.conn.send('530 Incorrect.\r\n')
    def QUIT(self,cmd):
        self.conn.send('221 Goodbye.\r\n')
    def NOOP(self,cmd):
        self.conn.send('200 OK.\r\n')
    def TYPE(self,cmd):
        self.mode=cmd[5]
        self.conn.send('200 Binary mode.\r\n')

    def CDUP(self,cmd):
        if not os.path.samefile(self.cwd,self.basewd):
            #learn from stackoverflow
            self.cwd=os.path.abspath(os.path.join(self.cwd,'..'))
        self.conn.send('200 OK.\r\n')
        
    def PWD(self,cmd):
        #TODO
        cwd='/'
        self.conn.send('257 \"%s\"\r\n' % cwd)
        
    def CWD(self,cmd):
        chwd=cmd[4:-2]
        #TODO
        if chwd == '/':
            self.conn.send('250 OK.\r\n')
        else:
            self.conn.send('550 Access Denied, Dude.\r\n')

    def PORT(self,cmd):
        if self.pasv_mode:
            self.servsock.close()
            self.pasv_mode = False
        l=cmd[5:].split(',')
        self.dataAddr='.'.join(l[:4])
        self.dataPort=(int(l[4])<<8)+int(l[5])
        self.conn.send('200 Get port.\r\n')

    def PASV(self,cmd): # from http://goo.gl/3if2U
        self.pasv_mode = True
        self.servsock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.servsock.bind((local_ip,0))
        self.servsock.listen(1)
        ip, port = self.servsock.getsockname()
        print 'open', ip, port
        self.conn.send('227 Entering Passive Mode (%s,%u,%u).\r\n' %
                (','.join(ip.split('.')), port>>8&0xFF, port&0xFF))

    def start_datasock(self):
        if self.pasv_mode:
            self.datasock, addr = self.servsock.accept()
            print 'connect:', addr
        else:
            self.datasock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.datasock.connect((self.dataAddr,self.dataPort))

    def stop_datasock(self):
        self.datasock.close()
        if self.pasv_mode:
            self.servsock.close()


    def LIST(self,cmd):
        self.conn.send('150 Here comes the directory listing.\r\n')
        print 'list:', self.cwd
        self.start_datasock()
        for o in self.game.items:
            self.datasock.send(self.toListItem(o) + '\r\n')
        self.stop_datasock()
        self.conn.send('226 Directory send OK.\r\n')

    def toListItem(self, o):
        fullmode='rwxrwxrwx'
        d = o.isDir and 'd' or '-'
        ftime=time.strftime(' %b %d %H:%M ', time.localtime())
        return d+fullmode+' 1 user group 1'+ftime+o.name

    def MKD(self,cmd):
        dn=os.path.join(self.cwd,cmd[4:-2])
        os.mkdir(dn)
        self.conn.send('257 Directory created.\r\n')

    def RMD(self,cmd):
        dn=os.path.join(self.cwd,cmd[4:-2])
        if allow_delete:
            os.rmdir(dn)
            self.conn.send('250 Directory deleted.\r\n')
        else:
            self.conn.send('450 Not allowed.\r\n')

    def DELE(self,cmd):
        was_deleted = self.game.removeItemByName(cmd[5:-2])
        if was_deleted:
            self.conn.send('250 File deleted.\r\n')
        else:
            self.conn.send('450 Not allowed.\r\n')

    def RNFR(self,cmd):
        self.rnfn=os.path.join(self.cwd,cmd[5:-2])
        self.conn.send('350 Ready.\r\n')

    def RNTO(self,cmd):
        fn=os.path.join(self.cwd,cmd[5:-2])
        os.rename(self.rnfn,fn)
        self.conn.send('250 File renamed.\r\n')

    def REST(self,cmd):
        self.pos=int(cmd[5:-2])
        self.rest=True
        self.conn.send('250 File position reseted.\r\n')

    def RETR(self,cmd):
        fn=os.path.join(self.cwd,cmd[5:-2])
        #fn=os.path.join(self.cwd,cmd[5:-2]).lstrip('/')
        print 'Downloading:',fn
        if self.mode=='I':
            fi=open(fn,'rb')
        else:
            fi=open(fn,'r')
        self.conn.send('150 Opening data connection.\r\n')
        if self.rest:
            fi.seek(self.pos)
            self.rest=False
        data= fi.read(1024)
        self.start_datasock()
        while data:
            self.datasock.send(data)
            data=fi.read(1024)
        fi.close()
        self.stop_datasock()
        self.conn.send('226 Transfer complete.\r\n')

    def SIZE(self,cmd):
        self.conn.send('213 100\r\n')

    def STOR(self,cmd):
        fn=os.path.join(self.cwd,cmd[5:-2])
        print 'Uploading:',fn
        if self.mode=='I':
            fo=open(fn,'wb')
        else:
            fo=open(fn,'w')
        self.conn.send('150 Opening data connection.\r\n')
        self.start_datasock()
        while True:
            data=self.datasock.recv(1024)
            if not data: break
            fo.write(data)
        fo.close()
        self.stop_datasock()
        self.conn.send('226 Transfer complete.\r\n')

class FTPserver(threading.Thread):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((local_ip,local_port))
        threading.Thread.__init__(self)

    def run(self):
        self.sock.listen(5)
        while True:
            th=FTPserverThread(self.sock.accept())
            th.daemon=True
            th.start()

    def stop(self):
        self.sock.close()

if __name__=='__main__':
    ftp=FTPserver()
    ftp.daemon=True
    ftp.start()
    print 'On', local_ip, ':', local_port
    raw_input('Enter to end...\n')
    ftp.stop()
