import asyncio
import logging
from aioftp.server import User, Server
import pathlib
from gamepathio import GamePathIO, GameUser
from gameengine import GameEngine
import functools

engine = GameEngine()
user = GameUser(engine=engine, login="anonymous", base_path=pathlib.PurePosixPath("/"))
OurGamePathIO = functools.partial(GamePathIO, root=engine)
server = Server([user], path_io_factory=OurGamePathIO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="[%H:%M:%S]:",
)

loop = asyncio.get_event_loop()
loop.run_until_complete(server.start("127.0.0.1", 21))
try:

    loop.run_forever()

except KeyboardInterrupt:

    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
