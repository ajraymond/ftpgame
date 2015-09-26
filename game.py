#!/usr/bin/env python2
# coding: utf-8

import os,socket,threading,time
import re
#import traceback

allow_delete = False
local_ip = '127.0.0.1'
local_port = 21
currdir=os.path.abspath('.')


class GameItem:
    def __init__(self, name, parent, isDir, isLocked, contains, data):
        self.name = name

        self.parent = parent
        self.items = contains

        self.isDir = isDir
        self.isLocked = isLocked
        self.data = data
        
    def __str__(self):
        return "GameItem " + self.name
        
    def remove(self):
        return self.parent.removeChild(self)
        
    def addChild(self, item):
        self.items.append(item)
        item.parent = self
        
    # returns true if (at least?) 1 item was deleted
    def removeChild(self, item):
        oldItemCount = len(self.items)
        self.items = [o for o in self.items if (o.name != item.name or o.isLocked)]
        itemWasDeleted = len(self.items) < oldItemCount
        return itemWasDeleted
                       
    def getItem(self, pathList):
        myItem = [o for o in self.items if (o.name == pathList[0])]
        if len(myItem) < 1:
            print "Error cannot find item ", pathList
            return None
        if len(pathList) == 1:
            return myItem[0]
        else:
            return myItem[0].getItem(pathList[1:])

    def getURL(self):
        partialURL = "/" + self.name
        if self.parent is None:
            return partialURL
        else:
            if self.parent.parent is None:
                return partialURL
            else:
                return self.parent.getURL() + partialURL
            
# a level (scene?) with ropes and a locked door; when the ropes are deleted, the door opens
class Level0(GameItem):
    def __init__(self, parent):
        GameItem.__init__(self, "0", parent, True, False, [], '')
        self.items = [ GameItem("rope-1", self, False, False, [], 'rope1'),  
                       GameItem("rope-2", self, False, False, [], 'rope2'),
                       GameItem("door", self, True, True, [], '') ]
     
        # on this level, the door opens if all ropes are cut
        
    def removeChild(self, item):
        retVal = GameItem.removeChild(self, item)
        numberOfRopes = len([o for o in self.items if o.name.startswith("rope")])
        if numberOfRopes == 0:
            for x in [o for o in self.items if o.name.startswith("door")]:
                x.name = "door-open"
                x.isLocked = False
        return retVal
                
# a single room
class Level1(GameItem):
    def __init__(self, parent):
        GameItem.__init__(self, "1", parent, True, False, [], '')
        self.items = [ GameItem("folder", self, True, True, [], '') ]

# a hierarchy of folders and items
class Level2(GameItem):
    def __init__(self, parent):
        GameItem.__init__(self, "2", parent, True, False, [], '')
        prev = self
        for x in range(3):
            i = GameItem("sword-level-" + str(x), prev, False, False, [], str(x))
            prev.items.append(i)
            folder = GameItem("folder-" + str(x), prev, True, False, [], '')
            prev.items.append(folder)
            prev = folder
        
class Level3(GameItem):
    def __init__(self, parent):
        GameItem.__init__(self, "3", parent, True, True, [], '')

class Level4(GameItem):
    def __init__(self, parent):
        GameItem.__init__(self, "4", parent, True, True, [], '')

class GameRoot(GameItem):
    def __init__(self):
        GameItem.__init__(self, "", None, True, False, [], '')
        self.NUM_LEVELS = 4
        self.items = []
        for i in range(self.NUM_LEVELS):
            self.items.append(globals()['Level' + str(i)](self)) #pffft
    
    def getItemByURL(self, URL, cwd):
        if URL == '/':
            return self;
        else:
            target = cwd
            if re.match('/.*', URL):
                # absolute URL
                target = self
            m = re.findall('([^/]+)', URL)
            return target.getItem(m)
    
    #for upload
    #returns tuple (targetFileName, targetLocation)
    def getItemAndLocationbyURL(self, URL, cwd):
        #TODO there's an unlikely possibility that we get a path
        #     that is relative to the current cwd; could be improved
        target = cwd
        m = re.match('(?P<absolute>/)?(?P<path>.*/)?(?P<filename>[^/]+)', URL)
        if m.group('absolute'):
            target = self.getItemByURL("/" + m.group('path'), cwd)
        return (m.group('filename'), target)

sharedGame = GameRoot()
            
class FTPserverThread(threading.Thread):
    def __init__(self,(conn,addr)):
        self.conn=conn
        self.addr=addr
        self.rest=False
        self.pasv_mode=False
        self.root = sharedGame
        self.cwd = self.root
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
        
    def XPWD(self, cmd):
        self.PWD(cmd)
        
    def PWD(self, cmd):
        URL = self.cwd.getURL()
        self.conn.send('257 \"%s\"\r\n' % URL)
        
    def CWD(self,cmd):
        requestedDir = cmd[4:-2]
        baseURL = self.cwd
        item = self.root.getItemByURL(requestedDir, baseURL)
        if not item is None and item.isDir and not item.isLocked:
            self.conn.send('250 OK.\r\n')
            self.cwd = item
        else:
            #returning Access Denied because a more descriptive message
            # might reveal what is hiding, say, behind a closed door
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
        self.start_datasock()   
        #TODO do something if cwd doesn't exist/isn't accessible (unlikely?)
        for o in self.cwd.items:
            self.datasock.send(self.toListItem(o) + '\r\n')
        self.stop_datasock()
        self.conn.send('226 Directory send OK.\r\n')

    def toListItem(self, o):
        fullmode='rwxrwxrwx'
        d = o.isDir and 'd' or '-'
        ftime=time.strftime(' %b %d %H:%M ', time.localtime())
        return d+fullmode+' 1 user group '+str(len(o.data))+' '+ftime+o.name

    def MKD(self,cmd):
        dn = os.path.join(self.cwd, cmd[4:-2])
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
        was_deleted = False
        
        requestedURL = cmd[5:-2]
        baseURL = self.cwd
        file = self.root.getItemByURL(requestedURL, baseURL)
        if not file is None:
            was_deleted = file.remove()
        
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
        requestedURL = cmd[5:-2]
        baseURL = self.cwd
        item = self.root.getItemByURL(requestedURL, baseURL)
        if item is None:
            self.conn.send('450 Access Denied.\r\n')
        else:
            print 'Downloading:' + requestedURL
            #TODO check if we're in binary mode with self.mode=='I':
            self.conn.send('150 Opening data connection.\r\n')
            #TODO check if RESTore mode? unsure
            #TODO break down into pieces, like 1024 bytes...
            data = item.data
            self.start_datasock()
            try:
                sent = self.datasock.sendall(data)
            except socket.error:
                print 'Send failed: ' + sent
            self.stop_datasock()
            self.conn.send('226 Transfer complete.\r\n')

    def SIZE(self,cmd):
        self.conn.send('213 100\r\n')

    def ABOR(self,cmd):
        self.conn.send('426 Never gonna give you up.\r\n')

    def SITE(self, cmd):
        self.conn.send('200 OK whatever man.\r\n')
        
    def STOR(self,cmd):
        filePath = cmd[5:-2]
        print 'Uploading: ' + filePath
        #TODO check if binary mode
        #TODO check if cwd is still writeable (unlikely?)
        #TODO check if file already exists there
        self.conn.send('150 Opening data connection.\r\n')
        self.start_datasock()
        allData = []
        while True:
            data=self.datasock.recv(1024)
            if not data: break
            allData.append(data)
        self.stop_datasock()
        bigString = ''.join(allData)
        
        (fileName, target) = self.root.getItemAndLocationbyURL(filePath, self.cwd)
        
        newItem = GameItem(fileName, self.cwd, False, False, [], bigString)
        self.cwd.addChild(newItem)
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
