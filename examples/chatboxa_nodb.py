import sys
import asyncio
import telepot
from telepot.delegate import per_chat_id_in
from telepot.async.delegate import call, create_open

""" Python3.4.3 or newer

$ python3.4 chatboxa_nodb.py <token> <owner_id>

Chatbox - a mailbox for chats

1. People send messages to your bot.
2. Your bot remembers the messages.
3. You read the messages later.

This version only stores the messages in memory. If the bot is killed, all messages are lost.
This version only handles text messages.

It accepts the following commands from you, the owner, only:

- /unread - tells you who has sent you messages and how many
- /next - read next sender's messages

It can be a starting point for customer-support type of bots.
"""

# Simulate a database to store unread messages
class UnreadStore(object):
    def __init__(self):
        self._db = {}

    def put(self, msg):
        chat_id = msg['chat']['id']
        
        if chat_id not in self._db:
            self._db[chat_id] = []

        self._db[chat_id].append(msg)

    # Pull all unread messages of a `chat_id`
    def pull(self, chat_id):
        messages = self._db[chat_id]
        del self._db[chat_id]
        
        # sort by date
        messages.sort(key=lambda m: m['date'])
        return messages

    # Tells how many unread messages per chat_id
    def unread_per_chat(self):
        return [(k,len(v)) for k,v in self._db.items()]


# Accept commands from owner. Give him unread messages.
class OwnerHandler(telepot.helper.ChatHandler):
    def __init__(self, seed_tuple, timeout, store):
        super(OwnerHandler, self).__init__(seed_tuple, timeout)
        self._store = store

    @asyncio.coroutine
    def _read_messages(self, messages):
        for msg in messages:
            # assume all messages are text
            yield from self.sender.sendMessage(msg['text'])

    @asyncio.coroutine
    def on_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance2(msg)

        if content_type != 'text':
            yield from self.sender.sendMessage("I don't understand")
            return

        command = msg['text'].strip().lower()

        # Tells who has sent you how many messages
        if command == '/unread':
            results = self._store.unread_per_chat()

            lines = []
            for r in results:
                n = 'ID: %d\n%d unread' % r
                lines.append(n)

            if not len(lines):
                yield from self.sender.sendMessage('No unread messages')
            else:
                yield from self.sender.sendMessage('\n'.join(lines))

        # read next sender's messages
        elif command == '/next':
            results = self._store.unread_per_chat()

            if not len(results):
                yield from self.sender.sendMessage('No unread messages')
                return

            chat_id = results[0][0]
            unread_messages = self._store.pull(chat_id)

            yield from self.sender.sendMessage('From ID: %d' % chat_id)
            yield from self._read_messages(unread_messages)

        else:
            yield from self.sender.sendMessage("I don't understand")


class MessageSaver(telepot.helper.Monitor):
    def __init__(self, seed_tuple, store, exclude):
        # The `capture` criteria means to capture all messages.
        super(MessageSaver, self).__init__(seed_tuple, capture=[{'_': lambda msg: True}])
        self._store = store
        self._exclude = exclude

    # Store every message, except those whose sender is in the exclude list, or non-text messages.
    def on_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance2(msg)

        if chat_id in self._exclude:
            print('Chat id %d is excluded.' % chat_id)
            return

        if content_type != 'text':
            print('Content type %s is ignored.' % content_type)
            return

        print('Storing message: %s' % msg)
        self._store.put(msg)


class ChatBox(telepot.async.DelegatorBot):
    def __init__(self, token, owner_id):
        self._owner_id = owner_id
        self._seen = set()
        self._store = UnreadStore()

        super(ChatBox, self).__init__(token, [
            # Here is a delegate to specially handle owner commands.
            (per_chat_id_in([owner_id]), create_open(OwnerHandler, 20, self._store)),

            # Seed is always the same, meaning only one MessageSaver is ever spawned for entire application.
            (lambda msg: 1, create_open(MessageSaver, self._store, exclude=[owner_id])),

            # For senders never seen before, send him a welcome message.
            (self._is_newcomer, call(self._send_welcome)),
        ])

    # seed-calculating function: use returned value to indicate whether to spawn a delegate
    def _is_newcomer(self, msg):
        chat_id = msg['chat']['id']
        if chat_id == self._owner_id:  # Sender is owner
            return None  # No delegate spawned

        if chat_id in self._seen:  # Sender has been seen before
            return None  # No delegate spawned

        self._seen.add(chat_id)
        return []  # non-hashable ==> delegates are independent, no seed association is made.

    @asyncio.coroutine
    def _send_welcome(self, seed_tuple):
        chat_id = seed_tuple[1]['chat']['id']

        print('Sending welcome ...')
        yield from self.sendMessage(chat_id, 'Hello!')


TOKEN = sys.argv[1]
OWNER_ID = int(sys.argv[2])

bot = ChatBox(TOKEN, OWNER_ID)
loop = asyncio.get_event_loop()

loop.create_task(bot.messageLoop())
print('Listening ...')

loop.run_forever()
