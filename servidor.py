#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import tornado.web
import tornado.websocket
import tornado.ioloop
import asyncio
import websockets


# Gestión del teclado
import evdev
import select
import json

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("public/index.html")

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    def open(self):
        print("WebSocket connection opened")
        WebSocketHandler.clients.add(self)

    async def on_message(self, message):
        # Maneja el mensaje recibido a través del WebSocket
        print("Received message: " + message)
        await WebSocketHandler.broadcast("Received message: " + message)

    async def broadcast(self, message):
        for client in self.clients:
            client.write_message(message)

    def on_close(self):
        print("WebSocket connection closed")
        WebSocketHandler.clients.remove(self)

class GetHandler(tornado.web.RequestHandler):
    async def get(self):
        global almacen
        if "timestamp" in self.request.arguments:
            # Obtener el primer valor enviado para "variable"
            try:
                timestamp = self.get_argument("timestamp") + 0.01
                print("Obtenido timestamp: " + timestamp)
                if almacen["timestamp"] > timestamp:
                    print("Enviamos palabra")
                    self.write(almacen["palabra"])
                    return
            except:
                pass
        try:
            async with websockets.connect('ws://localhost:8888/ws/') as websocket:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    print("Recibido (sin timeout): " + message)
                    try:
                        message = json.loads(message)
                        if "palabra" in message:
                            if "timestamp" in message:
                                self.write(str(message["timestamp"]) + ";" + message["palabra"])
                            else:
                                self.write(message["palabra"])
                    except Exception as e:
                        print(e)
                        #pass
                except asyncio.TimeoutError:
                    self.set_status(504)
                    self.write("Gateway Timeout")
                await websocket.close()
        except asyncio.exceptions.TimeoutError:
            self.set_status(504)
            self.write("Gateway Timeout")
        finally:
            self.finish()

class PostHandler(tornado.web.RequestHandler):
    async def get(self):
        #async with websockets.connect('ws://localhost:8888/ws/') as websocket:
        await WebSocketHandler.broadcast(WebSocketHandler, self.request.query)
        #    await websocket.finish()

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

almacen = {
    "palabra": "",
    "timestamp": 0,
}
async def broadcast():
    global anterior
    global almacen
    caps = False
    palabra = ""
    while True:
        await asyncio.sleep(0.001)
        r, w, x = select.select(dispositivos, [], [], 10)
        if len(r) == 0:
            print("Han pasado 10 segundos")
            actualizar()
            await WebSocketHandler.broadcast(WebSocketHandler, json.dumps({"dispositivos": {k: str(v) for k,v in dispositivos.items()}}))
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
                        almacen["timestamp"] = event.timestamp()
                        almacen["palabra"] = palabra
                        anterior = json.dumps({"palabra": palabra, "timestamp": event.timestamp()})
                        await WebSocketHandler.broadcast(WebSocketHandler, anterior)
                        palabra = ""
                    else:
                        try:
                            print(teclas[caps][event.code])
                            palabra += teclas[caps][event.code]
                        except KeyError:
                            pass

def make_app():
    websocket_handler = WebSocketHandler
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/esperar', GetHandler),
        (r'/enviar', PostHandler),
        (r'/ws/', websocket_handler),
        (r'/(.*)', tornado.web.StaticFileHandler, {'path': 'public'}),
    ], websocket_handler=websocket_handler)

if __name__ == "__main__":
    # Crea un bucle de eventos asyncio
    asyncio_loop = asyncio.get_event_loop()
    # Carga la función broadcast en un Task y ejecútala en paralelo con el bucle de eventos asyncio
    asyncio_loop.create_task(broadcast())

    app = make_app()
    app.listen(8888)
    print("Servidor iniciado en http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()
