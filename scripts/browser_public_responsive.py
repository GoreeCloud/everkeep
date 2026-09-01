#!/usr/bin/env python3
"""Exercise the built Continuity Center at screenshot-relevant viewport widths."""
from __future__ import annotations
import json
from pathlib import Path
import shutil, subprocess, tempfile, time
from typing import Any
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]; SITE=ROOT/"dist"; WEB_PORT=8765; DRIVER_PORT=9518
BASE=f"http://127.0.0.1:{DRIVER_PORT}"; TARGET=f"http://127.0.0.1:{WEB_PORT}/"; VIEWPORTS=((1180,900),(768,900),(390,844),(320,844))
class BrowserError(RuntimeError):pass
def require(ok:bool,msg:str)->None:
    if not ok:raise BrowserError(msg)
def req(method:str,path:str,payload:dict[str,Any]|None=None)->Any:
    data=None if payload is None else json.dumps(payload).encode()
    with urlopen(Request(BASE+path,data=data,method=method,headers={"Content-Type":"application/json"}),timeout=25) as r:raw=r.read()
    if not raw:return None
    value=json.loads(raw.decode()).get("value")
    if isinstance(value,dict) and value.get("error"):raise BrowserError(f"{value.get('error')}: {value.get('message','')}")
    return value
def wait(url:str,driver:bool=False)->None:
    end=time.monotonic()+15;last=None
    while time.monotonic()<end:
        try:
            if driver:
                state=req("GET","/status")
                if isinstance(state,dict) and state.get("ready"):return
            else:
                with urlopen(url,timeout=1) as r:
                    if r.status==200:return
        except Exception as exc:last=exc
        time.sleep(.15)
    raise BrowserError(f"service not ready: {last}")
def driver_bin()->str:
    for candidate in (shutil.which("chromedriver"),"/usr/local/share/chromedriver-linux64/chromedriver"):
        if candidate and Path(candidate).is_file():return str(candidate)
    raise BrowserError("chromedriver unavailable")
def main()->int:
    server=driver=None;session=None;log_path=None
    try:
        require((SITE/"index.html").is_file(),"built Continuity Center missing; run build first")
        server=subprocess.Popen(["python3","-m","http.server",str(WEB_PORT),"--bind","127.0.0.1","--directory",str(SITE)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);wait(TARGET)
        with tempfile.NamedTemporaryFile(prefix="everkeep-chromedriver-",suffix=".log",delete=False) as log:
            log_path=log.name;driver=subprocess.Popen([driver_bin(),f"--port={DRIVER_PORT}","--allowed-ips=127.0.0.1"],stdout=log,stderr=subprocess.STDOUT)
        wait(BASE+"/status",True)
        value=req("POST","/session",{"capabilities":{"alwaysMatch":{"browserName":"chrome","goog:chromeOptions":{"args":["--headless=new","--no-sandbox","--disable-dev-shm-usage","--disable-background-networking","--disable-extensions","--no-first-run","--window-size=1180,900"]}}}});require(isinstance(value,dict) and isinstance(value.get("sessionId"),str),f"bad Chrome session: {value!r}");session=value["sessionId"]
        req("POST",f"/session/{session}/timeouts",{"implicit":0,"pageLoad":15000,"script":10000});req("POST",f"/session/{session}/url",{"url":TARGET})
        for requested,height in VIEWPORTS:
            req("POST",f"/session/{session}/window/rect",{"width":requested,"height":height,"x":0,"y":0})
            state=req("POST",f"/session/{session}/execute/sync",{"script":"""const h=document.querySelector('header'),m=document.querySelector('main');const hr=h?.getBoundingClientRect(),mr=m?.getBoundingClientRect();const links=[...document.querySelectorAll('header nav a')].map(x=>x.getBoundingClientRect()).filter(r=>r.width>0&&r.height>0);return {ready:document.readyState,w:innerWidth,sw:document.documentElement.scrollWidth,pos:h?getComputedStyle(h).position:'',hb:hr?.bottom||0,mt:mr?.top||0,minNav:links.length?Math.min(...links.map(r=>r.height)):0};""","args":[]})
            require(isinstance(state,dict),f"layout unreadable at {requested}px");w=int(state.get("w",requested));require(state.get("ready")=="complete",f"page incomplete at {w}px: {state}");require(int(state.get("sw",w+2))<=w+1,f"horizontal overflow at {w}px: {state}");require(state.get("pos") not in {"sticky","fixed"},f"header overlays content at {w}px: {state}");require(float(state.get("mt",0))+1>=float(state.get("hb",0)),f"main overlaps header at {w}px: {state}");require(float(state.get("minNav",0))>=47.5,f"navigation target below 48px at {w}px: {state}")
        print("Continuity Center responsive Chrome geometry passed at 1180, 768, 390, and 320px.");return 0
    except Exception as exc:
        print(f"Continuity Center responsive Chrome geometry failed: {exc}")
        if log_path:
            try:print(Path(log_path).read_text(errors="replace")[-6000:])
            except OSError:pass
        return 1
    finally:
        if session:
            try:req("DELETE",f"/session/{session}")
            except Exception:pass
        for p in (driver,server):
            if p:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        if log_path:
            try:Path(log_path).unlink()
            except OSError:pass
if __name__=="__main__":raise SystemExit(main())
