from quart import Quart, request, make_response, render_template, redirect
from JsonStore import JsonStore
from Animebyter import get_airing
from Downloader import downloader, store, login_qb, InvalidCredentialsException, checker
from asyncio import get_event_loop,gather
import os
from sys import stdout
import logging

logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO').upper(),stream=StreamHandler(stdout))
app = Quart(__name__,"/static")
base_url = os.getenv("base_url")

class LastAiring:
    airing = []
    def get(self):
        return self.airing
    def sett(self,a):
        self.airing = a
last_airing = LastAiring()

class FakeObj:
    def __init__(self,dc):
        for i in dc.keys():
            setattr(self,i,dc[i])

@app.route("/")
async def home():
    airing = await get_airing()
    last_airing.sett(airing)
    watching = store["watching"]
    try:
        dl_path = store["downloadPath"]
    except KeyError:
        dl_path = ""
    try:
        dl_label = store["downloadLabel"]
    except KeyError:
        dl_label = ""
    return await render_template('index.html', airing=airing, watching=[FakeObj(i) for i in watching], dl_path=dl_path, dl_label=dl_label)

@app.route("/addAnime")
async def add_show():
    id = request.args.get("id")
    la = last_airing.get()
    show = None
    for i in la:
        if i.id == id:
            show = i
            break
    if show:
        watching = store["watching"]
        watching.append(vars(show))
        store["watching"] = watching
        return redirect(base_url)
    else:
        return await render_template("error.html", message="Show does not exist")

@app.route("/removeAnime")
async def remove_show():
    id = request.args.get("id")
    watching = store["watching"]
    for i in watching:
        if id == i['id']:
            watching.remove(i)
            store["watching"] = watching
            return redirect(base_url)
    return await render_template("error.html",message="Show does not exist")

@app.route("/updatePath", methods=["POST"])
async def set_path():
    path = (await request.form).get("path")
    if os.path.isdir(path):
        store["downloadPath"] = path
        return redirect(base_url)
    else:
        return await render_template("error.html", message="{} is not a valid path".format(path))

@app.route("/updateLabel", methods=["POST"])
async def set_label():
    label = (await request.form).get("label")
    store["downloadLabel"] = label
    return redirect(base_url)

@app.route("/updateCreds", methods=["POST"])
async def update_creds():
    form = await request.form
    username = form.get("user")
    password = form.get("password")
    try:
        await login_qb(username, password)
        store["qbUser"] = username
        store["qbPass"] = password
        return redirect(base_url)
    except InvalidCredentialsException:
        return await render_template("error.html", message="Invalid credentials. Try again")


if __name__ == '__main__':
    server_task = app.run_task("0.0.0.0")
    loop = get_event_loop()

    loop.run_until_complete(gather(server_task,downloader(),checker()))