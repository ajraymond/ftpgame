import asyncio
import collections
import operator
import io
from aioftp import AbstractPathIO
from aioftp.server import User, Permission
from gameengine import GameItem, Room, ItemKind


class GameUser(User):
    def __init__(self, engine=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = engine

    def get_node(self, path):  # argh this is a duplicate of get_node in other class
        nodes = [self.root]
        node = None
        for part in path.parts:
            if not isinstance(nodes, list):
                return
            for node in nodes:
                if node.name == part:
                    nodes = node.content
                    break
            else:
                return
        return node

    def get_permissions(self, path):
        node = self.get_node(path)

        is_locked = False
        if node is not None:
            is_locked = node.is_locked

        return Permission(path, readable=not is_locked, writable=not is_locked)


class GamePathIO(AbstractPathIO):
    Stats = collections.namedtuple(
        "Stats",
        (
            "st_size",
            "st_ctime",
            "st_mtime",
            "st_nlink",
            "st_mode",
        )
    )

    def __init__(self, *, timeout=None, loop=None, root=None):
        super().__init__(timeout=timeout, loop=loop)
        self.root = root

    def __repr__(self):

        return repr(self.root)

    def get_node(self, path):
        node = None
        nodes = [self.root]
        for part in path.parts:

            if not isinstance(nodes, list):

                return

            for node in nodes:

                if node.name == part:

                    nodes = node.content
                    break

            else:

                return

        return node

    @asyncio.coroutine
    def exists(self, path):

        return self.get_node(path) is not None

    @asyncio.coroutine
    def is_dir(self, path):

        node = self.get_node(path)
        return not (node is None or node.kind != ItemKind.room)

    @asyncio.coroutine
    def is_file(self, path):

        node = self.get_node(path)
        return not (node is None or node.kind == ItemKind.room)

    @asyncio.coroutine
    def mkdir(self, path, *, parents=False):

        if self.get_node(path):

            raise FileExistsError

        elif not parents:

            parent = self.get_node(path.parent)
            if parent is None:

                raise FileNotFoundError

            elif not parent.kind == ItemKind.room:

                raise FileExistsError

            node = Room(path.name)
            parent.add_child(node)

        else:

            nodes = [self.root]
            parent = self.root
            for part in path.parts:

                if isinstance(nodes, list):

                    for node in nodes:

                        if node.name == part:

                            nodes = node.content
                            parent = node
                            break

                    else:

                        new_node = Room(name=part)
                        parent.add_child(new_node)
                        nodes = new_node.content
                        parent = new_node

                else:

                    raise FileExistsError

    @asyncio.coroutine
    def rmdir(self, path):

        node = self.get_node(path)
        if node is None:

            raise FileNotFoundError

        elif node.kind != ItemKind.room:

            raise NotADirectoryError

        elif node.content:

            raise OSError("Directory not empty")

        else:

            node.remove()

    @asyncio.coroutine
    def unlink(self, path):

        node = self.get_node(path)
        if node is None:

            raise FileNotFoundError

        elif node.kind == ItemKind.room:

            raise IsADirectoryError

        else:

            node.remove()

    @asyncio.coroutine
    def list(self, path):

        node = self.get_node(path)
        if node is None or node.kind != ItemKind.room:

            return ()

        else:

            names = map(operator.attrgetter("name"), node.content)
            paths = map(lambda name: path / name, names)
            return tuple(paths)

    @asyncio.coroutine
    def stat(self, path):

        node = self.get_node(path)
        if node is None:

            raise FileNotFoundError

        else:

            size = len(node.content)

            return self.Stats(
                size,
                0,
                0,
                1,
                0o100777,
            )

    @asyncio.coroutine
    def open(self, path, mode="rb", *args, **kwargs):

        if mode == "rb":

            node = self.get_node(path)
            if node is None:

                raise FileNotFoundError

            data = node.content.encode('utf-8')
            file_like = io.BytesIO(data)

        elif mode in ("wb", "ab"):

            node = self.get_node(path)
            parent = self.get_node(path.parent)
            if parent is None or parent.kind != ItemKind.room:

                raise FileNotFoundError

            if node is None:

                file_like = (io.BytesIO(), parent, path.name)

            elif node.kind != ItemKind.regular:

                raise IsADirectoryError

            else:

                previous_content = node.content
                node.remove()

                if mode == "wb":

                    file_like = (io.BytesIO(), parent, path.name)

                else:

                    file_like = (io.BytesIO(previous_content.encode('utf-8')), parent, path.name)

        else:

            raise ValueError(str.format("invalid mode: {}", mode))

        return file_like

    @asyncio.coroutine
    def write(self, file, data):

        if isinstance(file, tuple):
            (stream, parent, name) = file
            stream.write(data)
            # file.mtime = int(time.time())

    @asyncio.coroutine
    def read(self, file, count=None):

        return file.read(count)

    @asyncio.coroutine
    def close(self, file):
        if isinstance(file, tuple):
            # we're writing to a file, so commit the whole thing to the item tree
            (stream, parent, name) = file

            data = stream.getvalue().decode()
            parent.add_child(GameItem(name, content=data))
        else:
            pass

    @asyncio.coroutine
    def rename(self, source, destination):

        if source != destination:

            sparent = self.get_node(source.parent)
            dparent = self.get_node(destination.parent)
            snode = self.get_node(source)
            if None in (snode, dparent):

                raise FileNotFoundError

            for i, node in enumerate(sparent.content):

                if node.name == source.name:

                    node.remove()

            snode.name = destination.name
            for i, node in enumerate(dparent.content):

                if node.name == destination.name:

                    dparent.content[i] = snode
                    break

            else:

                dparent.add_child(snode)
