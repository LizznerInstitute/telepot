# coding=utf8

import time
import threading
import pprint
import sys
import traceback
import telepot

"""
This script tests these, in sequence:
- setWebhook() and getUpdates(), and make sure they are exclusive
- sendZZZ() and sendChatAction() methods
- getUserProfilePhotos()
- switching message handlers by calling notifyOnMessage() a few times
- receiving all types of messages, by asking user to produce each

Run it by:
$ python test.py <token> <user_id>

It will assume the bot identified by <token>, and only communicate with the user identified by <user_id>.

If you don't know your user id, run:
$ python test.py <token> 0

And send it a message anyway. It will print out your user id as an unauthorized user.
Ctrl-C to kill it, then run the proper command again.
"""

def equivalent(data, nt):
    if type(data) is dict:
        keys = list(data.keys())

        # number of dictionary keys == number of non-None values in namedtuple?        
        if len(keys) != len([f for f in nt._fields if getattr(nt, f) is not None]):
            return False

        # map `from` to `from_`
        fields = list([k+'_' if k in ['from'] else k for k in keys])
        
        return all(map(equivalent, [data[k] for k in keys], [getattr(nt, f) for f in fields]))
    elif type(data) is list:
        return all(map(equivalent, data, nt))
    else:
        return data==nt

def examine(result, type):
    try:
        print('Examining %s ......' % type)

        nt = telepot.namedtuple(result, type)
        assert equivalent(result, nt), 'Not equivalent:::::::::::::::\n%s\n::::::::::::::::\n%s' % (result, nt)

        if type == 'Message':
            print('Message glance2: %s' % str(telepot.glance2(result, long=True)))

        pprint.pprint(result)
        pprint.pprint(nt)
        print()
    except AssertionError:
        traceback.print_exc()
        answer = input('Do you want to continue? [y] ')
        if answer != 'y':
            exit(1)

def send_everything_on_contact(msg):
    content_type, chat_type, chat_id, msg_date, msg_id = telepot.glance2(msg, long=True)

    if chat_id != USER_ID:
        print('Unauthorized user:', msg['from']['id'])
        exit(1)

    print('Received message from ID: %d' % chat_id)
    print('Start sending various messages ...')

    ##### forwardMessage
    
    r = bot.forwardMessage(chat_id, chat_id, msg_id)
    examine(r, 'Message')

    ##### sendMessage

    r = bot.sendMessage(chat_id, 'Hello, I am going to send you a lot of things.', reply_to_message_id=msg_id)
    examine(r, 'Message')

    r = bot.sendMessage(chat_id, '中文')
    examine(r, 'Message')

    r = bot.sendMessage(chat_id, '*bold text*\n_italic text_\n[link](http://www.google.com)', parse_mode='Markdown')
    examine(r, 'Message')

    bot.sendMessage(chat_id, 'http://www.yahoo.com\nwith web page preview')

    bot.sendMessage(chat_id, 'http://www.yahoo.com\nno web page preview', disable_web_page_preview=True)

    show_keyboard = {'keyboard': [['Yes', 'No'], ['Maybe', 'Maybe not']]}
    bot.sendMessage(chat_id, 'Here is a custom keyboard', reply_markup=show_keyboard)

    time.sleep(2)

    hide_keyboard = {'hide_keyboard': True}
    bot.sendMessage(chat_id, 'Hiding it now.', reply_markup=hide_keyboard)

    force_reply = {'force_reply': True}
    bot.sendMessage(chat_id, 'Force reply', reply_markup=force_reply)

    ##### sendPhoto

    bot.sendChatAction(chat_id, 'upload_photo')
    r = bot.sendPhoto(chat_id, open('lighthouse.jpg', 'rb'))
    examine(r, 'Message')

    file_id = r['photo'][0]['file_id']

    bot.sendPhoto(chat_id, file_id, caption='Show original message and keyboard', reply_to_message_id=msg_id, reply_markup=show_keyboard)

    bot.sendPhoto(chat_id, file_id, caption='Hide keyboard', reply_markup=hide_keyboard)

    ##### getFile
    
    f = bot.getFile(file_id)
    examine(f, 'File')

    ##### downloadFile, smaller than one chunk (65K)
    
    try:
        print('Downloading file to non-existent directory ...')
        bot.downloadFile(file_id, 'non-existent-dir/file')
    except:
        print('Error: as expected')

    print('Downloading file to down.1 ...')
    bot.downloadFile(file_id, 'down.1')

    print('Open down.2 and download to it ...')
    with open('down.2', 'wb') as down:
        bot.downloadFile(file_id, down)

    ##### sendAudio
    # Need one of `performer` or `title' for server to regard it as audio. Otherwise, server treats it as voice.

    bot.sendChatAction(chat_id, 'upload_audio')
    r = bot.sendAudio(chat_id, open('dgdg.mp3', 'rb'), title='Ringtone')
    examine(r, 'Message')

    file_id = r['audio']['file_id']

    bot.sendAudio(chat_id, file_id, duration=6, performer='Ding Dong', title='Ringtone', reply_to_message_id=msg_id, reply_markup=show_keyboard)

    bot.sendAudio(chat_id, file_id, performer='Ding Dong', reply_markup=hide_keyboard)

    ##### sendDocument

    bot.sendChatAction(chat_id, 'upload_document')
    r = bot.sendDocument(chat_id, open('document.txt', 'rb'))
    examine(r, 'Message')

    file_id = r['document']['file_id']

    bot.sendDocument(chat_id, file_id, reply_to_message_id=msg_id, reply_markup=show_keyboard)

    bot.sendDocument(chat_id, file_id, reply_markup=hide_keyboard)

    ##### sendSticker

    r = bot.sendSticker(chat_id, open('gandhi.png', 'rb'))
    examine(r, 'Message')

    file_id = r['sticker']['file_id']

    bot.sendSticker(chat_id, file_id, reply_to_message_id=msg_id, reply_markup=show_keyboard)

    bot.sendSticker(chat_id, file_id, reply_markup=hide_keyboard)

    ##### sendVideo

    bot.sendChatAction(chat_id, 'upload_video')
    r = bot.sendVideo(chat_id, open('hktraffic.mp4', 'rb'))
    examine(r, 'Message')

    file_id = r['video']['file_id']

    bot.sendVideo(chat_id, file_id, duration=5, caption='Hong Kong traffic', reply_to_message_id=msg_id, reply_markup=show_keyboard)

    bot.sendVideo(chat_id, file_id, reply_markup=hide_keyboard)

    ##### downloadFile, multiple chunks

    print('Downloading file to down.3 ...')
    bot.downloadFile(file_id, 'down.3')

    ##### sendVoice

    r = bot.sendVoice(chat_id, open('example.ogg', 'rb'))
    examine(r, 'Message')

    file_id = r['voice']['file_id']

    bot.sendVoice(chat_id, file_id, duration=6, reply_to_message_id=msg_id, reply_markup=show_keyboard)

    bot.sendVoice(chat_id, file_id, reply_markup=hide_keyboard)

    ##### sendLocation

    bot.sendChatAction(chat_id, 'find_location')
    r = bot.sendLocation(chat_id, 22.33, 114.18)  # Hong Kong
    examine(r, 'Message')

    bot.sendLocation(chat_id, 49.25, -123.1, reply_to_message_id=msg_id, reply_markup=show_keyboard)  # Vancouver

    bot.sendLocation(chat_id, -37.82, 144.97, reply_markup=hide_keyboard)  # Melbourne

    ##### Done sending messages

    bot.sendMessage(chat_id, 'I am done.')
    done.set()

def get_user_profile_photos():
    print('Getting user profile photos ...')

    r = bot.getUserProfilePhotos(USER_ID)
    examine(r, 'UserProfilePhotos')

def handle1(msg):
    if msg['from']['id'] != USER_ID:
        print('Unauthorized user:', msg['from']['id'])
        return

    print('1. Received message from ID: %d' % msg['from']['id'])
    print('Content:', msg['text'])

def handle2(msg):
    if msg['from']['id'] != USER_ID:
        print('Unauthorized user:', msg['from']['id'])
        return

    print('^^2^^ Received message from ID: %d' % msg['from']['id'])
    print('Content:', msg['text'])

def handle3(msg):
    if msg['from']['id'] != USER_ID:
        print('Unauthorized user:', msg['from']['id'])
        return

    print('-----3----- Received message from ID: %d' % msg['from']['id'])
    print('Content:', msg['text'])

keep_active_thread_counter = True

def print_active_thread_count():
    global keep_active_thread_counter

    while keep_active_thread_counter:
        print('Number of active threads: %d' % threading.active_count())
        time.sleep(5)

def switch_msg_handlers():
    t = threading.Thread(target=print_active_thread_count)
    t.daemon = True
    t.start()

    print('I am listening with handle1() ...')
    bot.notifyOnMessage(handle1)
    time.sleep(30)

    print('I am listening with handle2() ...')
    bot.notifyOnMessage(handle2, timeout=0)
    time.sleep(30)

    print('I am listening with handle3() ...')
    bot.notifyOnMessage(handle3)
    time.sleep(30)

    done.set()

    global keep_active_thread_counter
    keep_active_thread_counter = False

expected_content_type = None
content_type_iterator = iter([
    'text', 'voice', 'sticker', 'photo', 'audio' ,'document', 'video', 'contact', 'location',
    'new_chat_participant',  'new_chat_title', 'new_chat_photo',  'delete_chat_photo', 'left_chat_participant'
])

def see_every_content_types(msg):
    global expected_content_type, content_type_iterator

    content_type, chat_type, chat_id = telepot.glance2(msg)
    from_id = msg['from']['id']

    if chat_id != USER_ID and from_id != USER_ID:
        print('Unauthorized user:', chat_id, from_id)
        return

    examine(msg, 'Message')
    try:
        if content_type == expected_content_type:
            expected_content_type = next(content_type_iterator)
            bot.sendMessage(chat_id, 'Please give me a %s.' % expected_content_type)
        else:
            bot.sendMessage(chat_id, 'It is not a %s. Please give me a %s, please.' % (expected_content_type, expected_content_type))
    except StopIteration:
        # reply to sender because I am kicked from group already
        bot.sendMessage(from_id, 'Thank you. I am done.')
        done.set()

def ask_for_various_messages():
    bot.notifyOnMessage(see_every_content_types)

    global expected_content_type, content_type_iterator
    expected_content_type = next(content_type_iterator)

    bot.sendMessage(USER_ID, 'Please give me a %s.' % expected_content_type)

def test_webhook_getupdates_exclusive():
    bot.setWebhook('https://www.fake.com/fake', open('old.cert', 'rb'))
    print('Fake webhook set.')
    
    try:
        bot.getUpdates()
    except telepot.TelegramError as e:
        print("%d: %s" % (e.error_code, e.description))
        print('As expected, getUpdates() produces an error.')

    bot.setWebhook()
    print('Fake webhook cancelled.')


TOKEN = sys.argv[1]
USER_ID = int(sys.argv[2])

bot = telepot.Bot(TOKEN)

test_webhook_getupdates_exclusive()

print('Text me to start.')
done = threading.Event()
bot.notifyOnMessage(send_everything_on_contact)
done.wait()

get_user_profile_photos()

done.clear()
switch_msg_handlers()
done.wait()

done.clear()
ask_for_various_messages()
done.wait()

print('Test finished. Exit.')
