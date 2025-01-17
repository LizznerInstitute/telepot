import time
import traceback
import threading
import logging
import telepot
import telepot.filtering
from functools import partial

try:
    import Queue as queue
except ImportError:
    import queue


class Microphone(object):
    def __init__(self):
        self._queues = set()
        self._lock = threading.Lock()

    def _locked(func):
        def k(self, *args, **kwargs):
            with self._lock:
                func(self, *args, **kwargs)
        return k

    @_locked
    def add(self, q):
        self._queues.add(q)

    @_locked
    def remove(self, q):
        self._queues.remove(q)

    @_locked
    def send(self, msg):
        for q in self._queues:
            try:
                q.put_nowait(msg)
            except queue.Full:
                traceback.print_exc()


class WaitTooLong(telepot.TelepotException):
    pass


class Listener(object):
    def __init__(self, mic, q):
        self._mic = mic
        self._queue = q

        self._criteria = []

        self._options = {
            'timeout': None,
        }

    def __del__(self):
        self._mic.remove(self._queue)

    def set_options(self, **name_values):
        self._options.update(name_values)

    def get_options(self, *names):
        return tuple(map(lambda n: self._options[n], names))

    def capture(self, **criteria):
        self._criteria.append(criteria)

    def cancel_capture(self, **criteria):
        # remove duplicates
        self._criteria = list(filter(lambda c: c != criteria, self._criteria))

    def clear_captures(self):
        del self._criteria[:]

    def list_captures(self):
        return self._criteria

    def wait(self):
        if not self._criteria:
            raise RuntimeError('Listener has no capture criteria, will wait forever.')

        def meet_some_criteria(msg):
            return any(map(lambda c: telepot.filtering.ok(msg, **c), self._criteria))

        timeout, = self.get_options('timeout')

        if timeout is None:
            while 1:
                msg = self._queue.get(block=True)

                if meet_some_criteria(msg):
                    return msg
        else:
            end = time.time() + timeout

            while 1:
                timeleft = end - time.time()

                if timeleft < 0:
                    raise WaitTooLong()

                try:
                    msg = self._queue.get(block=True, timeout=timeleft)
                except queue.Empty:
                    raise WaitTooLong()

                if meet_some_criteria(msg):
                    return msg


class Sender(object):
    def __init__(self, bot, chat_id):
        for method in ['sendMessage',
                       'forwardMessage',
                       'sendPhoto',
                       'sendAudio',
                       'sendDocument',
                       'sendSticker',
                       'sendVideo',
                       'sendVoice',
                       'sendLocation',
                       'sendChatAction',]:
            setattr(self, method, partial(getattr(bot, method), chat_id))
            # Essentially doing:
            #   self.sendMessage = partial(bot.sendMessage, chat_id)


class ListenerContext(object):
    def __init__(self, bot, context_id):
        self._bot = bot
        self._id = context_id
        self._listener = bot.create_listener()

    @property
    def bot(self):
        return self._bot

    @property
    def id(self):
        return self._id

    @property
    def listener(self):
        return self._listener


class ChatContext(ListenerContext):
    def __init__(self, bot, context_id, chat_id):
        super(ChatContext, self).__init__(bot, context_id)
        self._chat_id = chat_id
        self._sender = Sender(bot, chat_id)

    @property
    def chat_id(self):
        return self._chat_id

    @property
    def sender(self):
        return self._sender


class StopListening(telepot.TelepotException):
    def __init__(self, code=None, reason=None):
        super(StopListening, self).__init__(code, reason)

    @property
    def code(self):
        return self.args[0]

    @property
    def reason(self):
        return self.args[1]


def openable(cls):
    def open(self, *arg, **kwargs):
        pass

    def on_message(self, *arg, **kwargs):
        raise NotImplementedError()

    def on_close(self, exception):
        logging.error('on_close() called due to %s: %s', type(exception).__name__, exception)

    def close(self, code=None, reason=None):
        raise StopListening(code, reason)

    @property
    def listener(self):
        raise NotImplementedError()

    def ensure_method(name, fn):
        if getattr(cls, name, None) is None:
            setattr(cls, name, fn)

    # set attribute if no such attribute
    ensure_method('open', open)
    ensure_method('on_message', on_message)
    ensure_method('on_close', on_close)
    ensure_method('close', close)
    ensure_method('listener', listener)

    return cls


@openable
class Monitor(ListenerContext):
    def __init__(self, seed_tuple, capture):
        bot, initial_msg, seed = seed_tuple
        super(Monitor, self).__init__(bot, seed)

        for c in capture:
            self.listener.capture(**c)


@openable
class ChatHandler(ChatContext):
    def __init__(self, seed_tuple, timeout):
        bot, initial_msg, seed = seed_tuple
        super(ChatHandler, self).__init__(bot, seed, initial_msg['chat']['id'])
        self.listener.set_options(timeout=timeout)
        self.listener.capture(chat__id=self.chat_id)
