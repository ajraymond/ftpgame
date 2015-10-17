"""Prototype of a game played via FTP

Usage: ftpgame [options]

Options:
    -q, --quiet             disable logging to stderr
    -a, --async             use asynchronous FTP server (experimental)
    --host=host             host for binding [default: 127.0.0.1]
    --port=port             port for binding [default: 21]
"""
import asyncio
import logging
import docopt
import functools
import pathlib

import aioftp

import gameengine
import threaded_server
import aio_helpers

args = docopt.docopt(__doc__)

engine = gameengine.GameEngine()


if not args["--quiet"]:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="[%H:%M:%S]:",
    )

if not args["--async"]:
    ftp = threaded_server.FTPserver(engine, args["--host"], int(args["--port"]))
    ftp.daemon = True
    ftp.start()
    print('On', args["--host"], ':', args["--port"])
    input('Enter to end...\n')
    ftp.stop()

else:
    user = aio_helpers.GameUser(engine=engine, login="anonymous", base_path=pathlib.PurePosixPath("/"))
    OurGamePathIO = functools.partial(aio_helpers.GamePathIO, root=engine)
    server = aioftp.Server([user], path_io_factory=OurGamePathIO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start(args["--host"], int(args["--port"])))
    try:

        loop.run_forever()

    except KeyboardInterrupt:

        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
