# IRC interface for Stack Overflow chat

This is an IRC interface to Stack Overflow chat.
This program is an IRC server which you run on your local machine, and you connect to it on its port (6668 by default) using any IRC client.

In the spirit of "the simplest thing that can possibly work", there are currently limitations:

- the only connected channel is "Chat Feedback" (77)
- everything you say is echoed back to you
- encoded entities like &quot; are not decoded
- everything is undoubtedly fragile

You must copy `soirc.config.sample` to `soirc.config` and insert your `somusr` cookie value from your browser.
Then, run `soirc.py` and connect to localhost port 6668 with your IRC client.
