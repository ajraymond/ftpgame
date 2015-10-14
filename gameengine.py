# TODO
# TODO
# TODO
# change is_dir to an item.type
# change content to be either data (file), message (NPC) or a list (other files)

# monitor the list contents instead of using add_child, delete_child

import re
import uuid
from enum import Enum


class ItemType(Enum):
    regular = 1
    room = 2
    npc = 3


class GameItem(object):
    def __init__(self, name, type=ItemType.regular, is_locked=False, content=None, watches=None,
                 message=None, message_stor=None, message_dele=None, message_retr=None):
        self._name = name
        self.type = type

        self.parent = None
        self.content = content or []
        if isinstance(content, list):
            for x in self.content:
                x.parent = self

        self.is_locked = is_locked

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
        return self._name + ("-locked" if self.is_locked and self.type == ItemType.room else "")

    @name.setter
    def name(self, value):
        self._name = value

    def add_child(self, item):
        self.content.append(item)
        item.parent = self
        self.notify_observers()

    def remove(self, force=False):
        return self.parent.remove_child(self, force)

    # returns true if (at least?) 1 item was deleted
    def remove_child(self, item, force=False):
        item_was_deleted = False
        if item in self.content:
            self.content.remove(item)
            item_was_deleted = True
            self.notify_observers()
        return item_was_deleted

    def get_url(self):
        if self.parent is None:
            return self.name
        elif self.parent.parent is None:
            return "/" + self.name
        else:
            return self.parent.get_url() + "/" + self.name

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
        return self.contains

    @property
    def watches(self):
        return self._watches

    # action is a function that takes the watched element as a parameter
    # condition is a function with no parameters
    def add_watch(self, condition, action):
        self.watches.append((condition, action))

    # TODO add event types?
    def notify_observers(self):
        for (condition, action) in self.watches:
            if condition(self):
                action(self)

    # TODO move the path handling to the main game class, using pathlib's parser instead of recursion
    def get_item(self, path_list):
        my_item = [o for o in self.content if (o.name == path_list[0])]
        if len(my_item) < 1:
            print("Error cannot find item ", path_list)
            return None
        if len(path_list) == 1:
            return my_item[0]
        else:
            return my_item[0].get_item(path_list[1:])


# a regular game item, with an auto-generated unique key
class UniqueItem(GameItem):
    def __init__(self, *args, **kwargs):
        kwargs['content'] = str(uuid.uuid4())
        super(UniqueItem, self).__init__(*args, **kwargs)

    # returns a lambda that will return true if there is an item with the specified data in the specified folder
    # this is convenient for conditions, because [] == False
    @staticmethod
    def unique_item_in_folder(item_data):
        return lambda folder: [o for o in folder.content if o.content == item_data]


class Room(GameItem):
    def __init__(self, *args, **kwargs):
        kwargs['type'] = ItemType.room
        super(Room, self).__init__(*args, **kwargs)


# hides all items except shiny ones until the room is lit
class DarkRoom(Room):
    def __init__(self, is_lit=False, *args, **kwargs):
        self.is_lit = is_lit
        super(DarkRoom, self).__init__(*args, **kwargs)

    @property
    def content(self):
        all_items = self._content
        if self.is_lit:
            return all_items
        else:
            all_shiny_items = [o for o in all_items if getattr(o, 'is_shiny', False)]
            return all_shiny_items

    @content.setter
    def content(self, new_content):
        self._content = new_content

    def get_item(self, path_list):
        real_item = super(DarkRoom, self).get_item(path_list)
        if self.is_lit or getattr(real_item, 'is_shiny', False):
            return real_item
        else:
            return None


# shiny items are visible even in dark rooms
class ShinyItem(GameItem):
    def __init__(self, *args, **kwargs):
        self.is_shiny = True
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
        return lambda folder: [o for o in folder.all_items if o.content == item_data]


class GameEngine(GameItem):
    def __init__(self):
        GameItem.__init__(self, name="/", type=ItemType.room)
        zippo = UniqueItem("zippo")
        self.add_child(Room(name="1", content=[
            Room(name="folder", content=[
                Room(name="red-door"),
                zippo
            ]),
            DarkRoom(name="green-door", content=[
                ShinyItem(name="candelabra"),
                GameItem(name="secret-scroll", content="secret message!")
            ], watches=[(ShinyItem.shiny_item_in_folder(zippo.content),
                         lambda watchee: setattr(watchee, 'is_lit', True))])
        ]))

        princess_story = Room(name="4")
        self.add_child(princess_story)

        padlock = UniqueItem(name="rusty-padlock",
                             message_dele="The old padlock falls apart, leaving the door open.")
        princess_story.add_child(padlock)

        rusty_door = Room(name="rusty-door", is_locked=True)
        princess_story.add_child(rusty_door)
        princess_story.add_watch(lambda watchee: padlock not in watchee.content,
                                 lambda watchee: setattr(rusty_door, 'is_locked', False))

        golden_key = UniqueItem(name="golden-key")
        rusty_door.add_child(golden_key)

        golden_castle_gate = Room("golden-castle-gate", is_locked=True)
        princess_story.add_child(golden_castle_gate)
        princess_story.add_watch(UniqueItem.unique_item_in_folder(golden_key.content),
                       lambda watchee: setattr(golden_castle_gate, 'is_locked', False))

        castle = Room("castle", is_locked=True,
                      message_stor="Is this a gift for me? Is this a letter at last?!")
        golden_castle_gate.add_child(castle)
        guard = GameItem("weak-guard",
                         message_dele="How dare you attack me! Hm, this loot really doesn't help me fight ba--")
        golden_castle_gate.add_child(guard)
        iron = UniqueItem(name="iron")
        golden_castle_gate.add_watch(lambda watchee: guard not in watchee.content and
                                                     iron not in watchee.content,  # otherwise stuck in loop
                                     lambda watchee: [setattr(castle, 'is_locked', False),
                                                      golden_castle_gate.add_child(iron)])

        forge = Room("forge", message_stor="Let me see what you have given me...")
        princess_story.add_child(forge)
        blacksmith = GameItem("Godor-the-blacksmith", is_locked=True,
                              message="Give me some iron and I will forge you a sword!")
        forge.add_child(blacksmith)
        sword = UniqueItem(name="sword", message_retr="Here is a good, basic sword, my friend.")
        forge.add_watch(lambda watchee: UniqueItem.unique_item_in_folder(iron.content)(watchee) and
                                        sword not in forge.content,  # otherwise, stuck in add_child -> notification loop
                        lambda watchee: [map(lambda x: x.remove(),
                                             UniqueItem.unique_item_in_folder(iron.content)(watchee)),
                                         watchee.add_child(sword)])

        dragon = GameItem("fierce-dragon", is_locked=True, message="Come closer, for I am hungry!",
                          message_dele="You have slayed the dragon, the princess is yours... if she's in a good mood!")
        castle.add_child(dragon)
        princess = GameItem("Pissy-the-Princess", is_locked=True, message="I'm afraid of the dragon!")
        castle.add_child(princess)

        def kill_dragon(watchee):
            map(GameItem.remove, [o for o in watchee.content if o.content == sword.content])
            dragon.remove(force=True)
            princess.message = "I'm pissed, you never send me any love letters :("
            castle.add_watch(lambda inner_watchee: len([i for i in inner_watchee.content
                                                        if isinstance(i.content, str) and
                                                        i.content.upper() == "i love you".upper()]) > 0,
                             lambda inner_watchee: [setattr(princess, 'message',
                                                            "Nice. My bed is this way, you naughty knight!"),
                                                    setattr(princess, 'name', "Saucy-the-Sexy-Princess")])

        castle.add_watch(UniqueItem.unique_item_in_folder(sword.content), kill_dragon)

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
        #      that is relative to the current cwd; could be improved
        target = cwd
        m = re.match('(?P<absolute>/)?(?P<path>.*/)?(?P<filename>[^/]+)', url)
        if m.group('absolute'):
            target = self.get_item_by_url("/" + m.group('path'), cwd)
        return m.group('filename'), target
