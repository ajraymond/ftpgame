# coding: utf-8

import socket
import threading
import time

import gameengine

allow_delete = False
local_ip = '127.0.0.1'
local_port = 21




class FTPserverThread(threading.Thread):
    def __init__(self, sock):
        (conn, addr) = sock
        self.conn = conn
        self.addr = addr
        self.rest = False
        self.pasv_mode = False
        self.root = sharedGame
        self.cwd = self.root
        threading.Thread.__init__(self)

    def _to_list_item(self, o):
        access = "---------" if o.is_locked else 'rwxrwxrwx'
        d = o.type == gameengine.ItemType.room and 'd' or '-'
        ftime = time.strftime(' %b %d %H:%M ', time.localtime())
        return d + access + ' 1 user group ' + str(len(o.content)) + ' ' + ftime + o.name


    def run(self):
        self.write('220 Welcome!\r\n')
        while True:
            cmd = self.read()
            if not cmd:
                break
            else:
                print('Received:', cmd)
                try:
                    func = getattr(self, "ftp_" + cmd[:4].strip().lower())
                    func(cmd)
                except Exception as e:
                    print('ERROR:', e)
                    # traceback.print_exc()
                    self.write('500 Sorry.\r\n')

    def write(self, message, on_datasock=False):
        channel = self.conn if not on_datasock else self.datasock
        return channel.send(str.encode(message, "utf-8"))

    def read(self, buffersize=256, on_datasock=False):
        channel = self.conn if not on_datasock else self.datasock
        return channel.recv(buffersize).decode()

    def ftp_syst(self, cmd):
        self.write('215 UNIX Type: L8\r\n')

    def ftp_opts(self, cmd):
        if cmd[5:-2].upper() == 'UTF8 ON':
            self.write('200 OK.\r\n')
        else:
            self.write('451 Sorry.\r\n')

    def ftp_user(self, cmd):
        self.write('331 OK.\r\n')

    def ftp_pass(self, cmd):
        self.write('230 OK.\r\n')
        # self.write('530 Incorrect.\r\n')

    def ftp_quit(self, cmd):
        self.write('221 Goodbye.\r\n')

    def ftp_noop(self, cmd):
        self.write('200 OK.\r\n')

    def ftp_type(self, cmd):
        self.mode = cmd[5]
        self.write('200 Binary mode.\r\n')

    def ftp_xpwd(self, cmd):
        self.ftp_pwd(cmd)

    def ftp_pwd(self, cmd):
        url = self.cwd.get_url()
        self.write('257 \"%s\"\r\n' % url)

    def ftp_cdup(self, cmd):
        self.ftp_cwd("CWD ..\r\n")

    def ftp_cwd(self, cmd):
        requested_dir = cmd[4:-2]
        # treat ".." as special case, whether it comes from CDUP or was input literally
        if requested_dir.strip() == "..":
            item = self.cwd.parent
        else:
            base_url = self.cwd
            item = self.root.get_item_by_url(requested_dir, base_url)

        if item is not None and item.type == gameengine.ItemType.room and not item.is_locked:
            self.write('250 OK.\r\n')
            self.cwd = item
        else:
            # returning Access Denied because a more descriptive message
            # might reveal what is hiding, say, behind a closed door
            self.write('550 Access Denied, Dude.\r\n')

    def ftp_port(self, cmd):
        if self.pasv_mode:
            self.servsock.close()
            self.pasv_mode = False
        l = cmd[5:].split(',')
        self.data_addr = '.'.join(l[:4])
        self.data_port = (int(l[4]) << 8) + int(l[5])
        self.write('200 Get port.\r\n')

    def ftp_pasv(self, cmd):  # from http://goo.gl/3if2U
        self.pasv_mode = True
        self.servsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servsock.bind((local_ip, 0))
        self.servsock.listen(1)
        ip, port = self.servsock.getsockname()
        print('open', ip, port)
        self.write('227 Entering Passive Mode (%s,%u,%u).\r\n' %
                   (','.join(ip.split('.')), port >> 8 & 0xFF, port & 0xFF))

    def start_datasock(self):
        if self.pasv_mode:
            self.datasock, addr = self.servsock.accept()
            print('connect:', addr)
        else:
            self.datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.datasock.connect((self.data_addr, self.data_port))

    def stop_datasock(self):
        self.datasock.close()
        if self.pasv_mode:
            self.servsock.close()

    def ftp_list(self, cmd):
        self.write('150 Here comes the directory listing.\r\n')
        self.start_datasock()
        # TODO do something if cwd doesn't exist/isn't accessible (unlikely?)
        for o in self.cwd.content:
            self.write(self._to_list_item(o) + '\r\n', on_datasock=True)
        self.stop_datasock()
        self.write('226 Directory send OK.\r\n')

    def ftp_mkd(self, cmd):
        # TODO
        self.write('451 Not implemented.\r\n')

    def ftp_rmd(self, cmd):
        # TODO
        self.write('451 Not implemented.\r\n')

    def ftp_dele(self, cmd):
        was_deleted = False

        requested_url = cmd[5:-2]
        base_url = self.cwd
        item = self.root.get_item_by_url(requested_url, base_url)

        message = ''
        if item is not None:
            message = item.message_dele or "File deleted."
            was_deleted = item.remove()

        if was_deleted:
            self.write('250 ' + message + '\r\n')
        else:
            self.write('450 Not allowed.\r\n')

    def ftp_rnfr(self, cmd):
        # TODO
        self.write('451 Not implemented.\r\n')

    def ftp_rnto(self, cmd):
        # TODO
        self.write('451 Not implemented.\r\n')

    def ftp_rest(self, cmd):
        self.pos = int(cmd[5:-2])
        self.rest = True
        self.write('250 File position reset.\r\n')

    def ftp_retr(self, cmd):
        requested_url = cmd[5:-2]
        base_url = self.cwd
        item = self.root.get_item_by_url(requested_url, base_url)

        if item is None:
            self.write('450 Access Denied.\r\n')
        elif item.is_locked and isinstance(item.content, str):
            self.write('450 ' + item.content + '\r\n')
        else:
            print('Downloading:' + requested_url)
            # TODO check if we're in binary mode with self.mode=='I':
            self.write('150 Opening data connection.\r\n')
            # TODO check if RESTore mode? unsure
            # TODO break down into pieces, like 1024 bytes...
            data = item.content
            self.start_datasock()
            sent = "(unknown)"
            # TODO should check if we were able to send everything
            try:
                sent = self.write(data, on_datasock=True)
            except socket.error:
                print('Send failed: ' + sent)
            self.stop_datasock()
            message = item.message_retr or "Transfer complete."
            self.write('226 ' + message + '\r\n')

    def ftp_size(self, cmd):
        self.write('213 100\r\n')

    def ftp_abor(self, cmd):
        self.write('426 Never gonna give you up.\r\n')

    def ftp_site(self, cmd):
        self.write('200 OK whatever man.\r\n')

    def ftp_stor(self, cmd):
        file_path = cmd[5:-2]
        print('Uploading: ' + file_path)
        # TODO check if binary mode
        # TODO check if cwd is still writeable (unlikely?)
        # TODO check if file already exists there
        self.write('150 Opening data connection.\r\n')
        self.start_datasock()
        all_data = []
        while True:
            data = self.read(1024, on_datasock=True)
            if not data:
                break
            all_data.append(data)
        self.stop_datasock()
        big_string = ''.join(all_data)

        (file_name, target) = self.root.get_item_and_location_by_url(file_path, self.cwd)

        message = target.message_stor or "Transfer complete."

        new_item = gameengine.GameItem(name=file_name, content=big_string)
        self.cwd.add_child(new_item)
        self.write('226 ' + message + '\r\n')


class FTPserver(threading.Thread):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((local_ip, local_port))
        threading.Thread.__init__(self)

    def run(self):
        self.sock.listen(5)
        while True:
            th = FTPserverThread(self.sock.accept())
            th.daemon = True
            th.start()

    def stop(self):
        self.sock.close()


if __name__ == '__main__':
    sharedGame = gameengine.GameEngine()
    ftp = FTPserver()
    ftp.daemon = True
    ftp.start()
    print('On', local_ip, ':', local_port)
    input('Enter to end...\n')
    ftp.stop()
