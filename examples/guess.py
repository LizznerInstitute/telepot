import sys
import random
import telepot
from telepot.delegate import per_chat_id, create_open

"""
$ python2.7 guess.py <token>

Guess a number:

1. Send the bot anything to start a game.
2. The bot randomly picks an integer between 0-99.
3. You make a guess.
4. The bot tells you to go higher or lower.
5. Repeat step 3 and 4, until guess is correct.
"""

class Player(telepot.helper.ChatHandler):
    def __init__(self, seed_tuple, timeout):
        super(Player, self).__init__(seed_tuple, timeout)
        self._answer = random.randint(0,99)

    def _hint(self, answer, guess):
        if answer > guess:
            return 'larger'
        else:
            return 'smaller'

    def open(self, initial_msg, seed):
        self.sender.sendMessage('Guess my number')
        return True  # prevent on_message() from being called on the initial message

    def on_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance2(msg)

        if content_type != 'text':
            self.sender.sendMessage('Give me a number, please.')
            return

        try:
           guess = int(msg['text'])
        except ValueError:
            self.sender.sendMessage('Give me a number, please.')
            return

        # check the guess against the answer ...
        if guess != self._answer:
            # give a descriptive hint
            hint = self._hint(self._answer, guess)
            self.sender.sendMessage(hint)
        else:
            self.sender.sendMessage('Correct!')
            self.close()

    def on_close(self, exception):
        if isinstance(exception, telepot.helper.WaitTooLong):
            self.sender.sendMessage('Game expired. The answer is %d' % self._answer)


TOKEN = sys.argv[1]

bot = telepot.DelegatorBot(TOKEN, [
    (per_chat_id(), create_open(Player, timeout=10)),
])
bot.notifyOnMessage(run_forever=True)
