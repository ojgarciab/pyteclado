#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Gestión del teclado
import evdev
import select
import json

# Servidor websocket
import asyncio
import functools
import os
import sys
import time
import websockets

# Dispositivos disponibles (con la tecla ENTER)
dispositivos = {}

def actualizar():
    global dispositivos
    dispositivos.clear()
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        try:
            if device.capabilities()[1].index(28) >= 0:
                dispositivos[device.fd] = device
        except KeyError:
            pass
        except ValueError:
            pass
    print(dispositivos)

actualizar()

teclas = [
    {
        # Scancode: ASCIICode
        0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8',
        10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'q', 17: u'w', 18: u'e', 19: u'r',
        20: u't', 21: u'y', 22: u'u', 23: u'i', 24: u'o', 25: u'p', 26: u'[', 27: u']', 28: u'CRLF', 29: u'LCTRL',
        30: u'a', 31: u's', 32: u'd', 33: u'f', 34: u'g', 35: u'h', 36: u'j', 37: u'k', 38: u'l', 39: u';',
        40: u'"', 41: u'`', 42: u'LSHFT', 43: u'\\', 44: u'z', 45: u'x', 46: u'c', 47: u'v', 48: u'b', 49: u'n',
        50: u'm', 51: u',', 52: u'.', 53: u'/', 54: u'RSHFT', 56: u'LALT', 57: u' ', 100: u'RALT'
    },
    {
        0: None, 1: u'ESC', 2: u'!', 3: u'@', 4: u'#', 5: u'$', 6: u'%', 7: u'^', 8: u'&', 9: u'*',
        10: u'(', 11: u')', 12: u'_', 13: u'+', 14: u'BKSP', 15: u'TAB', 16: u'Q', 17: u'W', 18: u'E', 19: u'R',
        20: u'T', 21: u'Y', 22: u'U', 23: u'I', 24: u'O', 25: u'P', 26: u'{', 27: u'}', 28: u'CRLF', 29: u'LCTRL',
        30: u'A', 31: u'S', 32: u'D', 33: u'F', 34: u'G', 35: u'H', 36: u'J', 37: u'K', 38: u'L', 39: u':',
        40: u'\'', 41: u'~', 42: u'LSHFT', 43: u'|', 44: u'Z', 45: u'X', 46: u'C', 47: u'V', 48: u'B', 49: u'N',
        50: u'M', 51: u'<', 52: u'>', 53: u'?', 54: u'RSHFT', 56: u'LALT',  57: u' ', 100: u'RALT'
    },
]


# El set que contiene los clientes
CLIENTS = set()

anterior = ""

async def handler(websocket):
    global anterior
    CLIENTS.add(websocket)
    try:
        await websocket.send(anterior)
        await websocket.wait_closed()
    finally:
        CLIENTS.remove(websocket)


async def broadcast():
    global anterior
    caps = False
    palabra = ""
    while True:
        await asyncio.sleep(0.001)
        r, w, x = select.select(dispositivos, [], [], 2)
        if len(r) == 0:
            print("Han pasado 5 segundos")
            actualizar()
            websockets.broadcast(CLIENTS, json.dumps({"dispositivos": {k: str(v) for k,v in dispositivos.items()}}))
            continue
        for fd in r:
            for event in dispositivos[fd].read():
                print(event)
                if event.type == evdev.ecodes.EV_KEY:
                    if event.code == evdev.ecodes.KEY_LEFTSHIFT or event.code == evdev.ecodes.KEY_RIGHTSHIFT:
                        caps = event.value != evdev.events.KeyEvent.key_up
                        #print("Mayúsculas:")
                        #print(caps)
                    elif event.value == evdev.events.KeyEvent.key_up:
                        pass
                    elif event.code == evdev.ecodes.KEY_ENTER:
                        print("Palabra: " + palabra)
                        datos = {}
                        anterior = json.dumps({"palabra": palabra, "timestamp": event.timestamp(), "datos": datos})
                        websockets.broadcast(CLIENTS, anterior)
                        palabra = ""
                    else:
                        try:
                            print(teclas[caps][event.code])
                            palabra += teclas[caps][event.code]
                        except KeyError:
                            pass


async def main():
    async with websockets.serve(
        #functools.partial(handler, method=method),
        handler,
        "localhost",
        8765,
        compression=None,
        ping_timeout=None,
    ):
        await broadcast()


if __name__ == "__main__":
    asyncio.run(main())
