from Animebyter import get_airing
from asyncio import sleep, Queue, get_event_loop
from aiohttp import ClientSession
from JsonStore import JsonStore
import logging
import os

INTERVAL = int(os.getenv("interval","5"))
web = ClientSession()
QB_URL = os.getenv("qbit_url")
store = JsonStore(os.getenv("database"))
dl_queue = Queue(10)
loop = get_event_loop()

try:
    store["watching"]
except KeyError:
    store["watching"] = []
try:
    store["qbUser"]
except KeyError:
    store["qbUser"] = ""
try:
    store["qbPass"]
except KeyError:
    store["qbPass"] = ""

class InvalidCredentialsException(Exception):
    pass

class NotLoggedInException(Exception):
    pass

async def login_qb(username=store["qbUser"],password=store["qbPass"]):
    async with web.post(QB_URL+'/login',data={'username':username,'password':password}) as res:
        if res.status!=200:
            raise InvalidCredentialsException("Could not authenticate with qBittorrent.")
        else:
            logging.info("Logged into qBittorrent")

async def add_anime_torrent(anime):
    logging.info("Adding episode {} of {}".format(anime.last_episode,anime.title))
    path = os.path.join(store["downloadPath"],anime.title)
    async with web.post(QB_URL+'/command/download',data={'urls':anime.torrent_link,'savepath':path,'category':store["downloadLabel"]}) as res:
        if res.status==200:
            return 1
        elif res.status==403:
            raise NotLoggedInException()
        else:
            raise Exception(await res.text())

async def downloader():
    logging.info("Starting downloader")
    while True:
        anime = await dl_queue.get()
        while True:
            try:
                add_anime_torrent(anime)
                break
            except NotLoggedInException:
                while True:
                    try:
                        await login_qb()
                        break
                    except:
                        logging.warn("Could not log into qBittorrent. Trying again in 5 seconds")
                        await sleep(5)
                        continue
                continue
            except Exception as e:
                logging.error(str(e))

async def checker():
    logging.info("Starting new episode checker")
    while True:
        try:
            logging.debug("Checking for new episodes")
            airing = await get_airing()
            watching = store["watching"]
            for air in airing:
                for w_idx, watch in enumerate(watching):
                    if air.id == watch['id'] and air.last_episode > watch['last_episode']:
                        loop.create_task(dl_queue.put(air))
                        watching[w_idx]["last_episode"] = air.last_episode
                        store["watching"] = watching
        except Exception as e:
            logging.error(str(e))
            continue
        finally:
            await sleep(INTERVAL)