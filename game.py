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


class GameItem(object):
    def __init__(self, name, is_dir=False, is_locked=False, contains=None, watches=None, data="",
                 message=None, message_stor=None, message_dele=None, message_retr=None):
        self._name = name

        self.parent = None
        self._items = contains or []
        map(lambda i: setattr(i, 'parent', self), self._items)

        self.is_dir = is_dir
        self.is_locked = is_locked
        self.data = data

        self._message = message
        self._message_stor = message_stor
        self._message_dele = message_dele
        self._message_retr = message_retr

        # array of tuples (action, condition)
        self._watches = watches or []

    def __str__(self):
        return "GameItem " + self.name


    @property
    def name(self):
        """
        Item name as displayed to players.
        """
        return self._name + ("-locked" if self.is_locked and self.is_dir else "")

    @name.setter
    def name(self, value):
        self._name = value

    def remove(self, force=False):
        return self.parent.remove_child(self, force)

    def add_child(self, item):
        self._items.append(item)
        item.parent = self
        self.notify_observers()

    @property
    def message(self):
        """
        Message sent to the user when trying to retrieve an inaccessible item (e.g. talking to an NPC).
        """
        return self._message

    @message.setter
    def message(self, new_message):
        self._message = new_message

    @property
    def message_stor(self):
        """
        Message sent to the user after a file is successfully uploaded to the directory.
        """
        return self._message_stor

    @property
    def message_dele(self):
        """
        Message sent to the user as the item is deleted.
        """
        return self._message_dele

    @property
    def message_retr(self):
        """
        Message sent to the user as the item is successfully downloaded.
        """
        return self._message_retr

    @property
    def all_items(self):
        return self._items

    @property
    def items(self):
        """
        Items contained in this folder.
        """
        return self._items

    @property
    def watches(self):
        return self._watches

    # returns true if (at least?) 1 item was deleted
    def remove_child(self, item, force=False):
        item_was_deleted = False
        if item in self.items:
            self.items.remove(item)
            item_was_deleted = True
            self.notify_observers()
        return item_was_deleted

    # action is a function that takes the watched element as a parameter
    # condition is a function with no parameters
    def add_watch(self, condition, action):
        self.watches.append((condition, action))

    # TODO add event types?
    def notify_observers(self):
        for (condition, action) in self.watches:
            if condition(self):
                action(self)

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
    def __init__(self, *args, **kwargs):
        kwargs['data'] = str(uuid.uuid4())
        super(UniqueItem, self).__init__(*args, **kwargs)

    # returns a lambda that will return true if there is an item with the specified data in the specified folder
    # this is convenient for conditions, because [] == False
    @staticmethod
    def unique_item_in_folder(item_data):
        return lambda(folder): [o for o in folder.items if o.data == item_data]

class Room(GameItem):
    def __init__(self, *args, **kwargs):
        kwargs['is_dir'] = True
        super(Room, self).__init__(*args, **kwargs)

# hides all items except shiny ones until the room is lit
class DarkRoom(Room):
    def __init__(self, is_lit=False, *args, **kwargs):
        self._is_lit = is_lit
        super(DarkRoom, self).__init__(*args, **kwargs)

    @property
    def is_lit(self):
        return self._is_lit

    @is_lit.setter
    def is_lit(self, value):
        self._is_lit = value

    @property
    def items(self):
        all_items = super(DarkRoom, self).items
        if self.is_lit:
            return all_items
        else:
            all_shiny_items = [o for o in all_items if getattr(o, 'is_shiny', False)]
            return all_shiny_items

    def get_item(self, path_list):
        real_item = super(DarkRoom, self).get_item(path_list)
        if self.is_lit or getattr(real_item, 'is_shiny', False):
            return real_item
        else:
            return None

# shiny items are visible even in dark rooms
class ShinyItem(GameItem):

    @property
    def is_shiny(self):
        return self._is_shiny

    def __init__(self, *args, **kwargs):
        self._is_shiny = True
        super(ShinyItem, self).__init__(*args, **kwargs)

    @property
    def name(self):
        # TODO self.parent.is_lit is kind of a weird approach
        return super(ShinyItem, self).name + ("-lit" if self.parent.is_lit else "-unlit")

    # special version of item_in_folder than returns a lambda that will return true if there is
    # an item with the specified data in the specified folder; however this includes hidden objects
    # this is convenient for conditions, because [] == False
    @staticmethod
    def shiny_item_in_folder(item_data):
        return lambda(folder): [o for o in folder.all_items if o.data == item_data]


#empty
class Level0(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="0", is_dir=True)

# a single room
class Level1(GameItem):
    def __init__(self):
        zippo = UniqueItem("zippo")
        GameItem.__init__(self, name="1", is_dir=True, contains=[
            GameItem(name="folder", is_dir=True, contains=[
                Room(name="red-door"),
                zippo
            ]),
            DarkRoom(name="green-door", contains=[
                ShinyItem(name="candelabra"),
                GameItem(name="secret-scroll", data="secret message!")
            ], watches=[(ShinyItem.shiny_item_in_folder(zippo.data),
                         lambda watchee: setattr(watchee, 'is_lit', True))])
        ])



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


# cut 2 ropes to open door
# /!\ obsolete because checking for item names isn't very robust
class Level3(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="3", is_dir=True)
        self.add_child(GameItem(name="rope-1", data='rope1'))
        self.add_child(GameItem(name="rope-2", data='rope2'))
        door = GameItem("door", is_dir=True, is_locked=True)
        self.items.append(door)

        self.add_watch(lambda watchee: len([o for o in self.items if o.name.startswith("rope")]) == 0,
                       lambda watchee: setattr(door, 'is_locked', False),)


# a level with a simple story!
class Level4(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="4", is_dir=True)
        padlock = UniqueItem(name="rusty-padlock",
                             message_dele="The old padlock falls apart, leaving the door open.")
        self.add_child(padlock)

        rusty_door = GameItem(name="rusty-door", is_dir=True, is_locked=True)
        self.add_child(rusty_door)
        self.add_watch(lambda watchee: padlock not in watchee.items,
                       lambda watchee: setattr(rusty_door, 'is_locked', False))

        golden_key = UniqueItem(name="golden-key")
        rusty_door.add_child(golden_key)

        golden_door = GameItem("golden-door", is_dir=True, is_locked=True)
        self.add_child(golden_door)
        self.add_watch(UniqueItem.unique_item_in_folder(golden_key.data),
                       lambda watchee: setattr(golden_door, 'is_locked', False))

        castle = GameItem("castle", is_dir=True, is_locked=True,
                                message_stor="Is this a gift for me? Is this a letter at last?!")
        golden_door.add_child(castle)
        guard = GameItem("weak-guard",
                         message_dele="How dare you attack me! Hm, this loot really doesn't help me fight ba--")
        golden_door.add_child(guard)
        iron = UniqueItem(name="iron")
        golden_door.add_watch(lambda watchee: guard not in watchee.items and
                                              iron not in watchee.items, # without this, we're stuck in a add_child -> notification loop
                              lambda watchee: [setattr(castle, 'is_locked', False), golden_door.add_child(iron)])

        forge = GameItem("forge", is_dir=True, message_stor="Let me see what you have given me...")
        self.add_child(forge)
        blacksmith = GameItem("Godor-the-blacksmith", is_locked=True,
                              message="Give me some iron and I will forge you a sword!")
        forge.add_child(blacksmith)
        sword = UniqueItem(name="sword", message_retr="Here is a good, basic sword, my friend.")
        forge.add_watch(lambda(watchee): UniqueItem.unique_item_in_folder(iron.data)(watchee) and
                                         sword not in forge.items, # without this last item, we're stuck
                                                                   # in a add_child -> notification loop
                        lambda watchee: [map(lambda x: x.remove(), UniqueItem.unique_item_in_folder(iron.data)(watchee)),
                                         watchee.add_child(sword)])

        dragon = GameItem("fierce-dragon", is_locked=True, message="Come closer, for I am hungry!",
                          message_dele="You have slayed the dragon, the princess is yours... if she's in a good mood!")
        castle.add_child(dragon)
        princess = GameItem("Pissy-the-Princess", is_locked=True, message = "I'm afraid of the dragon!")
        castle.add_child(princess)

        def kill_dragon(watchee):
            map(GameItem.remove, [o for o in watchee.items if o.data == sword.data])
            dragon.remove(force=True)
            princess.message = "I'm pissed, you never send me any love letters :("
            castle.add_watch(lambda watchee: len([i for i in watchee.items
                                                  if i.data.upper() == "i love you".upper()]) > 0,
                             lambda watchee: [setattr(princess, 'message',
                                              "Nice. My bed is this way, you naughty knight!"),
                                              setattr(princess, 'name', "Saucy-the-Sexy-Princess")])
        castle.add_watch(UniqueItem.unique_item_in_folder(sword.data), kill_dragon)


class GameRoot(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="", is_dir=True)
        self.NUM_LEVELS = 5
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
    access = "---------" if o.is_locked else 'rwxrwxrwx'
    d = o.is_dir and 'd' or '-'
    ftime = time.strftime(' %b %d %H:%M ', time.localtime())
    return d + access + ' 1 user group ' + str(len(o.data)) + ' ' + ftime + o.name


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

    def ftp_xpwd(self, cmd):
        self.ftp_pwd(cmd)

    def ftp_pwd(self, cmd):
        url = self.cwd.get_url()
        self.conn.send('257 \"%s\"\r\n' % url)

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
            message = item.message_dele or "File deleted."
            was_deleted = item.remove()

        if was_deleted:
            self.conn.send('250 ' + message +'\r\n')
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
        elif item.is_locked and item.message is not None:
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
            message = item.message_retr or "Transfer complete."
            self.conn.send('226 ' + message + '\r\n')

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

        message = target.message_stor or "Transfer complete."

        new_item = GameItem(name=file_name, data=big_string)
        self.cwd.add_child(new_item)
        self.conn.send('226 ' + message + '\r\n')


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
