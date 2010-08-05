import cookielib
import json
import re
import select
import socket
import time
import urllib
import urllib2

Config = json.load(open("soirc.config"))

DEBUG = False

class IrcClient(object):
    def __init__(self, server, s):
        self.server = server
        self.sock = s
        self.data = ""
        self.nick = None
        self.user = None
        self.lastactivity = time.time()
        self.pingsent = False
    def socket(self):
        return self.sock
    def tick(self):
        silence = time.time() - self.lastactivity
        if silence > 300:
            self.sock.close()
            self.server.remove(self)
        elif silence > 150 and not self.pingsent:
            self.sock.send("PING :soirc\r\n")
            self.pingsent = True
    def handle(self):
        self.lastactivity = time.time()
        try:
            data = self.sock.recv(1024)
        except socket.error:
            self.sock.close()
            self.server.remove(self)
            return
        if len(data) == 0:
            self.sock.close()
            self.server.remove(self)
            return
        for c in data:
            if c == "\r":
                continue
            if c == "\n":
                if DEBUG: print "<-", self.data
                if ' ' in self.data:
                    command, params = self.data.split(" ", 1)
                else:
                    command = self.data
                    params = ""
                handler = getattr(self, "handle_" + command.lower(), None)
                if handler is not None:
                    response = handler(params)
                    if response:
                        if DEBUG: print "->", response
                        self.sock.send(response + "\r\n")
                else:
                    print "unknown command:", self.data
                self.data = ""
            else:
                self.data += c
    def handle_nick(self, params):
        nick = params
        if not re.match(r"[a-zA-Z0-9\-\[\]'`^{}_]+$", nick):
            print "bad nick", nick
            sys.exit(1)
        self.nick = nick
        return ":%s %s %s :soirc" % ("soirc", "001", self.nick)
    def handle_user(self, params):
        self.user, mode, _, realname = params.split(" ", 3)
        return ":%s JOIN :%s" % (self.ident(), "#soirc")
    def handle_ping(self, params):
        return ":%s PONG %s" % ("soirc", params)
    def handle_pong(self, params):
        self.pingsent = False
    def handle_privmsg(self, params):
        channel, msg = params.split(" ", 1)
        self.server.sender(self.nick, channel, msg[1:])
    def handle_quit(self, params):
        self.sock.close()
        self.server.remove(self)
    def handle_who(self, params):
        for f in friends:
            self.sock.send(":soirc 352 %s #soirc %s soirc soirc %s H :1 %s\r\n" % (self.nick, f['screen_name'], f['screen_name'], f['name']))
        self.sock.send(":soirc 315 %s :End of /WHO list" % self.nick)
    def ident(self):
        return "%s!%s@%s" % (self.nick, self.user, "soirc")
    def privmsg(self, user, channel, msg):
        self.sock.send(":%s PRIVMSG %s %s\r\n" % (user, channel, msg))

class IrcServer(object):
    def __init__(self, sender):
        self.sender = sender
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", Config['port']))
        self.sock.listen(5)
        self.clients = []
    def socket(self):
        return self.sock
    def tick(self):
        pass
    def handle(self):
        t, a = self.sock.accept()
        print "Client connect", a
        self.clients.append(IrcClient(self, t))
    def privmsg(self, user, channel, msg):
        for x in self.clients:
            x.privmsg(user, channel, msg)
    def remove(self, client):
        self.clients.remove(client)

class ChatServer(object):
    def __init__(self, room, sender):
        self.room = room
        self.sender = sender
        mainpage = opener.open("http://chat.meta.stackoverflow.com/rooms/%d/chat-feedback" % self.room).read()
        print cj
        assert "You must be" not in mainpage
        self.fkey = re.search(r"""id="fkey".*value="(\w+)" """, mainpage).group(1)
        print "fkey:", self.fkey
        self.lasttime = 0
        self.lasttick = 0
    def post(self, msg):
        opener.open("http://chat.meta.stackoverflow.com/chats/%d/messages/new" % self.room, urllib.urlencode({'fkey': self.fkey, 'text': msg}))
    def socket(self):
        return None
    def tick(self):
        now = time.time()
        if now - self.lasttick < 2:
            return
        self.lasttick = now
        jsdata = opener.open("http://chat.meta.stackoverflow.com/chats/%d/events?since=%d" % (self.room, self.lasttime), urllib.urlencode({'fkey': self.fkey})).read()
        try:
            data = json.loads(jsdata)
        except Exception as x:
            print x
            print jsdata
            self.lasttime = 0
            return
        if data['events']:
            print data['time'], len(data['events'])
        for e in data['events']:
            if e['event_type'] in (1, 2):
                self.sender(e['user_name'].replace(" ", ""), e['content'])
        self.lasttime = data['time']

cj = cookielib.CookieJar()
cj.set_cookie(cookielib.Cookie(None, "somusr", Config['cookie'], None, False, ".meta.stackoverflow.com", True, True, "/", True, False, None, False, None, None, None))
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

server = IrcServer(lambda user, channel, msg: sources[0].post(msg))
sources = []
for room in (77,):
    sources.append(ChatServer(room, lambda user, msg: server.privmsg("%s!%s@%s" % (user.encode("UTF-8"), user.encode("UTF-8"), "soirc"), "#soirc", msg.encode("UTF-8"))))

while True:
    a = sources + [server] + server.clients
    r, w, e = select.select([x.socket() for x in a if x.socket() is not None], [], [], 1)
    for x in r:
        for s in a:
            if x is s.socket():
                s.handle()
    for s in a:
        s.tick()
