#!/usr/bin/env python2
# coding: utf-8

import socket
import threading
import time
import re
import uuid

allow_delete = False
local_ip = '127.0.0.1'
local_port = 21


class GameItem:
    def __init__(self, name, is_dir=False, is_locked=False, contains=None, data=""):
        if not contains:
            contains = []
        self.name = name

        self.parent = None
        self.items = contains

        self.is_dir = is_dir
        self.is_locked = is_locked
        self.data = data

        self.observers = []
        self.callbacks = []

    def __str__(self):
        return "GameItem " + self.name

    def remove(self):
        return self.parent.remove_child(self)

    def add_child(self, item):
        self.items.append(item)
        item.parent = self
        self.notify_observers()

    # returns true if (at least?) 1 item was deleted
    def remove_child(self, item):
        old_item_count = len(self.items)
        self.items = [o for o in self.items if (o.name != item.name or o.is_locked)]
        item_was_deleted = len(self.items) < old_item_count
        if item_was_deleted:
            self.notify_observers()
        return item_was_deleted

    def observe(self, target, action):
        target.add_observer(self)
        self.callbacks.append(action)

    def trigger_event(self, source):
        for method in self.callbacks:
            method(self, source)

    # TODO maybe is there already such a module in python?
    def add_observer(self, observer):
        self.observers.append(observer)

    def remove_observer(self, observer):
        self.observers.remove(observer)

    # TODO add event types
    def notify_observers(self):
        for item in self.observers:
            item.trigger_event(self)

    def get_item(self, path_list):
        my_item = [o for o in self.items if (o.name == path_list[0])]
        if len(my_item) < 1:
            print("Error cannot find item ", path_list)
            return None
        if len(path_list) == 1:
            return my_item[0]
        else:
            return my_item[0].get_item(path_list[1:])

    def get_url(self):
        partial_url = "/" + self.name
        if self.parent is None:
            return partial_url
        else:
            if self.parent.parent is None:
                return partial_url
            else:
                return self.parent.get_url() + partial_url


# a regular game item, with an auto-generated unique key
class UniqueItem(GameItem):
    def __init__(self, name, is_dir=False, is_locked=False, contains=None):
        GameItem.__init__(self, name, is_dir, is_locked, contains, data=str(uuid.uuid4()))


# a level (scene?) with ropes and a locked door; when the ropes are deleted, the door opens
class Level0(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="0", is_dir=True)
        self.add_child(GameItem("rope-1", data='rope1'))
        self.add_child(GameItem("rope-2", data='rope2'))
        self.add_child(GameItem("door", is_dir=True, is_locked=True))

    def remove_child(self, item):
        ret_val = GameItem.remove_child(self, item)
        number_of_ropes = len([o for o in self.items if o.name.startswith("rope")])
        if number_of_ropes == 0:
            for x in [o for o in self.items if o.name.startswith("door")]:
                x.name = "door-open"
                x.is_locked = False
        return ret_val


# a single room
class Level1(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="1", is_dir=True)
        self.add_child(GameItem(name="folder", is_dir=True, is_locked=True))


# a hierarchy of folders and items
class Level2(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="2", is_dir=True)
        prev = self
        for x in range(3):
            i = GameItem(name="sword-level-" + str(x), data=str(x))
            prev.add_child(i)
            folder = GameItem(name="folder-" + str(x), is_dir=True)
            prev.add_child(folder)
            prev = folder


# an alternate implementation of Level 0
class Level3(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="3", is_dir=True)
        self.add_child(GameItem(name="rope-1", data='rope1'))
        self.add_child(GameItem(name="rope-2", data='rope2'))
        door = GameItem("door", is_dir=True, is_locked=True)
        self.items.append(door)

        def check_ropes(checking_door, folder):
            number_of_ropes = len([o for o in folder.items if o.name.startswith("rope")])
            if number_of_ropes == 0:
                checking_door.name = "door-open"
                checking_door.is_locked = False

        door.observe(self, check_ropes)


# a level with a simple story!
class Level4(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="4", is_dir=True)
        padlock = UniqueItem(name="rusty-padlock")
        self.add_child(padlock)

        rusty_door = GameItem(name="rusty-door-locked", is_dir=True, is_locked=True)
        self.add_child(rusty_door)
        # TODO turn this into a more formal, repeatable block
        def check_padlock(checking_door, folder):
            number_of_padlocks = len([o for o in folder.items if "padlock" in o.name])
            if number_of_padlocks == 0:
                checking_door.name = "rusty-door-open"
                checking_door.is_locked = False
        rusty_door.observe(self, check_padlock)

        golden_key = UniqueItem(name="golden-key")
        rusty_door.add_child(golden_key)

        golden_door = GameItem("golden-door-locked", is_dir=True, is_locked=True)
        self.add_child(golden_door)
        def check_golden_key(checking_door, folder):
            number_of_golden_keys = len([o for o in folder.items if golden_key.data == o.data])
            if number_of_golden_keys == 1:
                checking_door.name = "golden-door-open"
                checking_door.is_locked = False
        golden_door.observe(self, check_golden_key)

        guarded_door = GameItem("guarded-door", is_dir=True, is_locked=True)
        golden_door.add_child(guarded_door)
        guard = GameItem("weak-guard")
        golden_door.add_child(guard)
        def check_guard(checking_door, folder):
            number_of_guards = len([o for o in folder.items if "weak-guard" in o.name])
            number_of_irons = len([o for o in folder.items if "iron" in o.name])
            if number_of_guards == 0 and number_of_irons < 1: # TODO myeah - remove check instead?
                checking_door.name = "guarded-door-open"
                checking_door.is_locked = False
                golden_door.add_child(iron)
        guarded_door.observe(golden_door, check_guard)

        iron = UniqueItem(name="iron")
        sword = UniqueItem(name="sword")

        forge = GameItem("forge", is_dir=True)
        self.add_child(forge)
        blacksmith = GameItem("Godor-the-blacksmith", is_locked=True)
        blacksmith.message = "Give me some iron and I will forge you a sword!"
        forge.add_child(blacksmith)
        def check_for_iron(target, source): # in this case the forge is both source and target
            irons = [o for o in source.items if o.data == iron.data]
            number_of_irons = len(irons)
            if number_of_irons > 0:
                map(lambda x: x.remove(), irons)
                target.add_child(sword)
        forge.observe(forge, check_for_iron)

        dragon = GameItem("fierce-dragon", is_locked=True)
        guarded_door.add_child(dragon)
        dragon.message = "Come closer, for I am hungry!"
        princess = GameItem("Pissy-the-Princess", is_locked=True)
        princess.message = "I'm afraid of the dragon!"
        guarded_door.add_child(princess)
        def check_for_sword(target, source):
            swords = [o for o in source.items if o.data == sword.data]
            number_of_swords = len(swords)
            if number_of_swords > 0:
                map(lambda x: x.remove(), swords)
                dragon.remove()
                princess.message = "I'm pissed, you never send me any love letters :("
                guarded_door.observe(guarded_door, check_for_message)
        def check_for_message(target, source):
            messages = [o for o in source.items if o.data.upper() == "i love you".upper()]
            number_of_messages = len(messages)
            if number_of_messages > 0:
                princess.message = "Nice. My bed is this way, you naughty knight!"
                princess.name = "Saucy-the-Sexy-Princess"
        guarded_door.observe(guarded_door, check_for_sword)

class GameRoot(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="", is_dir=True)
        self.NUM_LEVELS = 5
        self.items = []
        for i in range(self.NUM_LEVELS):
            self.add_child(globals()['Level' + str(i)]())  # pffft

    def get_item_by_url(self, url, cwd):
        if url == '/':
            return self
        else:
            target = cwd
            if re.match('/.*', url):
                # absolute URL
                target = self
            m = re.findall('([^/]+)', url)
            return target.get_item(m)

    # for upload
    # returns tuple (targetFileName, targetLocation)
    def get_item_and_location_by_url(self, url, cwd):
        # TODO there's an unlikely possibility that we get a path
        #     that is relative to the current cwd; could be improved
        target = cwd
        m = re.match('(?P<absolute>/)?(?P<path>.*/)?(?P<filename>[^/]+)', url)
        if m.group('absolute'):
            target = self.get_item_by_url("/" + m.group('path'), cwd)
        return m.group('filename'), target


sharedGame = GameRoot()


def to_list_item(o):
    full_mode = 'rwxrwxrwx'
    d = o.is_dir and 'd' or '-'
    ftime = time.strftime(' %b %d %H:%M ', time.localtime())
    return d + full_mode + ' 1 user group ' + str(len(o.data)) + ' ' + ftime + o.name


class FTPserverThread(threading.Thread):
    def __init__(self, (conn, addr)):
        self.conn = conn
        self.addr = addr
        self.rest = False
        self.pasv_mode = False
        self.root = sharedGame
        self.cwd = self.root
        threading.Thread.__init__(self)

    def run(self):
        self.conn.send('220 Welcome!\r\n')
        while True:
            cmd = self.conn.recv(256)
            if not cmd:
                break
            else:
                print 'Received:', cmd
                try:
                    func = getattr(self, "ftp_" + cmd[:4].strip().lower())
                    func(cmd)
                except Exception, e:
                    print 'ERROR:', e
                    # traceback.print_exc()
                    self.conn.send('500 Sorry.\r\n')

    def ftp_syst(self, cmd):
        self.conn.send('215 UNIX Type: L8\r\n')

    def ftp_opts(self, cmd):
        if cmd[5:-2].upper() == 'UTF8 ON':
            self.conn.send('200 OK.\r\n')
        else:
            self.conn.send('451 Sorry.\r\n')

    def ftp_user(self, cmd):
        self.conn.send('331 OK.\r\n')

    def ftp_pass(self, cmd):
        self.conn.send('230 OK.\r\n')
        # self.conn.send('530 Incorrect.\r\n')

    def ftp_quit(self, cmd):
        self.conn.send('221 Goodbye.\r\n')

    def ftp_noop(self, cmd):
        self.conn.send('200 OK.\r\n')

    def ftp_type(self, cmd):
        self.mode = cmd[5]
        self.conn.send('200 Binary mode.\r\n')

    def ftp_cdup(self, cmd):
        # TODO
        self.conn.send('451 Not implemented.\r\n')

    def ftp_xpwd(self, cmd):
        self.ftp_pwd(cmd)

    def ftp_pwd(self, cmd):
        url = self.cwd.get_url()
        self.conn.send('257 \"%s\"\r\n' % url)

    def ftp_cwd(self, cmd):
        requested_dir = cmd[4:-2]
        base_url = self.cwd
        item = self.root.get_item_by_url(requested_dir, base_url)
        if item is not None and item.is_dir and not item.is_locked:
            self.conn.send('250 OK.\r\n')
            self.cwd = item
        else:
            # returning Access Denied because a more descriptive message
            # might reveal what is hiding, say, behind a closed door
            self.conn.send('550 Access Denied, Dude.\r\n')

    def ftp_port(self, cmd):
        if self.pasv_mode:
            self.servsock.close()
            self.pasv_mode = False
        l = cmd[5:].split(',')
        self.dataAddr = '.'.join(l[:4])
        self.dataPort = (int(l[4]) << 8) + int(l[5])
        self.conn.send('200 Get port.\r\n')

    def ftp_pasv(self, cmd):  # from http://goo.gl/3if2U
        self.pasv_mode = True
        self.servsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servsock.bind((local_ip, 0))
        self.servsock.listen(1)
        ip, port = self.servsock.getsockname()
        print 'open', ip, port
        self.conn.send('227 Entering Passive Mode (%s,%u,%u).\r\n' %
                       (','.join(ip.split('.')), port >> 8 & 0xFF, port & 0xFF))

    def start_datasock(self):
        if self.pasv_mode:
            self.datasock, addr = self.servsock.accept()
            print 'connect:', addr
        else:
            self.datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.datasock.connect((self.dataAddr, self.dataPort))

    def stop_datasock(self):
        self.datasock.close()
        if self.pasv_mode:
            self.servsock.close()

    def ftp_list(self, cmd):
        self.conn.send('150 Here comes the directory listing.\r\n')
        self.start_datasock()
        # TODO do something if cwd doesn't exist/isn't accessible (unlikely?)
        for o in self.cwd.items:
            self.datasock.send(to_list_item(o) + '\r\n')
        self.stop_datasock()
        self.conn.send('226 Directory send OK.\r\n')

    def ftp_mkd(self, cmd):
        # TODO
        self.conn.send('451 Not implemented.\r\n')

    def ftp_rmd(self, cmd):
        # TODO
        self.conn.send('451 Not implemented.\r\n')

    def ftp_dele(self, cmd):
        was_deleted = False

        requested_url = cmd[5:-2]
        base_url = self.cwd
        item = self.root.get_item_by_url(requested_url, base_url)
        if item is not None:
            was_deleted = item.remove()

        if was_deleted:
            self.conn.send('250 File deleted.\r\n')
        else:
            self.conn.send('450 Not allowed.\r\n')

    def ftp_rnfr(self, cmd):
        # TODO
        self.conn.send('451 Not implemented.\r\n')

    def ftp_rnto(self, cmd):
        # TODO
        self.conn.send('451 Not implemented.\r\n')

    def ftp_rest(self, cmd):
        self.pos = int(cmd[5:-2])
        self.rest = True
        self.conn.send('250 File position reseted.\r\n')

    def ftp_retr(self, cmd):
        requested_url = cmd[5:-2]
        base_url = self.cwd
        item = self.root.get_item_by_url(requested_url, base_url)
        if item is None:
            self.conn.send('450 Access Denied.\r\n')
        if item.is_locked and item.message is not None:
            self.conn.send('450 ' + item.message + '\r\n')
        else:
            print 'Downloading:' + requested_url
            # TODO check if we're in binary mode with self.mode=='I':
            self.conn.send('150 Opening data connection.\r\n')
            # TODO check if RESTore mode? unsure
            # TODO break down into pieces, like 1024 bytes...
            data = item.data
            self.start_datasock()
            sent = "(unknown)"
            try:
                sent = self.datasock.sendall(data)
            except socket.error:
                print 'Send failed: ' + sent
            self.stop_datasock()
            self.conn.send('226 Transfer complete.\r\n')

    def ftp_size(self, cmd):
        self.conn.send('213 100\r\n')

    def ftp_abor(self, cmd):
        self.conn.send('426 Never gonna give you up.\r\n')

    def ftp_site(self, cmd):
        self.conn.send('200 OK whatever man.\r\n')

    def ftp_stor(self, cmd):
        file_path = cmd[5:-2]
        print 'Uploading: ' + file_path
        # TODO check if binary mode
        # TODO check if cwd is still writeable (unlikely?)
        # TODO check if file already exists there
        self.conn.send('150 Opening data connection.\r\n')
        self.start_datasock()
        all_data = []
        while True:
            data = self.datasock.recv(1024)
            if not data:
                break
            all_data.append(data)
        self.stop_datasock()
        big_string = ''.join(all_data)

        (file_name, target) = self.root.get_item_and_location_by_url(file_path, self.cwd)

        new_item = GameItem(name=file_name, data=big_string)
        self.cwd.add_child(new_item)
        self.conn.send('226 Transfer complete.\r\n')


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
    ftp = FTPserver()
    ftp.daemon = True
    ftp.start()
    print 'On', local_ip, ':', local_port
    raw_input('Enter to end...\n')
    ftp.stop()
