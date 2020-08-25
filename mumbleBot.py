#!/usr/bin/env python3
# depends on 'pymumble'

# A mumble bot, plays music, tells fortunes.
# Uses youtube-dl as a backend.

import subprocess
import wave

from pymumble_py3.mumble    import Mumble
from pymumble_py3.callbacks import *

from subprocess import call
from sys        import argv
from os         import remove
from os         import listdir
from os.path    import join

# Helpers for command functions
def dynamicCall(function, alist):
    """Decompress a list into arguments dynamically."""
    try:
        return function(*alist)
    except TypeError:
        send_message("Wrong number of arguments.")

# Command functions
def debug(alst):
    def listToString(lst):
        x = ""
        for i in lst:
            x += str(i)
            x += ' '
        return x
    print(listToString(alst))
def stream(url):
    def findLastDownloadedFile():
        try:
            return join('/tmp',
                        [f for f in listdir('/tmp')
                         if f.find('video.') == 0][0])
        except IndexError:
            return ''
    # In case another thread is downloading something.
    try:
        remove(findLastDownloadedFile())
    except FileNotFoundError:pass

    try:
        if (len(url) > 1):
            if url[1].find('href') != -1:
                url = url[1]
                url = url[url.find('"')+1:url.find('">')]
            else: raise Error
        elif (len(url) == 1): url = url[0]
        else: raise BaseException
    except BaseException:
        send_message('Malformed or incorrect number of arguments to stream.')
        return

    send_message('Calling youtube-dl.')
    if call(['youtube-dl', '-x', url, '-o', '/tmp/video.%(ext)s']) == 0:
        send_message('Success downloading video.')
    else: send_message('Failure downloading video.')
    call(['ffmpeg', '-i', findLastDownloadedFile(), '-ac', '1',
         '/tmp/output.wav'])
    try:
        snd = wave.open('/tmp/output.wav')
        send_message('File opened and converted successfully.')
    except FileNotFoundError: # ffmpeg failed, fail silently
        send_message('Conversion failed.')
        return
    conn.sound_output.clear_buffer()
    conn.sound_output.add_sound(snd.readframes(snd.getnframes()))
    snd.close()

    remove('/tmp/output.wav')

def stop():
    conn.sound_output.clear_buffer()

def fortune():
    send_message(subprocess.run(['fortune'], stdout=subprocess.PIPE, universal_newlines=True).stdout)

def summon(originalMessage):
    user = conn.users[originalMessage.actor]
    send_message('Following ' + user.get_property('name') + '.')
    conn.channels[user.get_property('channel_id')].move_in()


# Globals
conn = None # Initialized later
commands = {
    "debug"  :(lambda alist, _:debug(alist)),
    "stream" :(lambda alist, _:stream(alist)),
    "stop"   :(lambda alist, _: dynamicCall(stop, alist)),
    "fortune":(lambda alist, _: dynamicCall(fortune, alist)),
    "summon" :(lambda alist, m: dynamicCall(summon, [m]+alist))
}

# Utility functions
def usage():
    print(argv[0] + " <server>[:<port>] <username>[:<password>]")
    exit(1)

def pullPair(string):
    try:
        idx = string.index(':')
        return (string[:idx], string[idx+1:])
    except ValueError: # no ':' in supplied string
        return (string, "")

def callCommand(commandString, argumentList, originalMessage):
    if commands.get(commandString):
        commands.get(commandString)(argumentList, originalMessage)
    else:
        send_message("Command '!" + commandString +
                          "' is not a defined command.")
def processMessage(message):
    messageString = message.message
    print("`"+conn.users[message.actor].get_property('name')+": "+
          messageString)
    if messageString.startswith('!'): # command character
        command = messageString[1:].split(' ')
        print("Calling command" + str(command) + "...")
        callCommand(command[0], command[1:], message)

def send_message(message):
    """ Send a message to the current channel of the bot."""
    conn.channels[conn.users.myself['channel_id']]\
        .send_text_message(message)

if __name__ == "__main__":
    # Local connection variables
    host     = ""      # server is currently mandatory: no default
    port     = ""      # default port: 64738
    uname    = ""      # username is currently mandatory: no default
    password = ""

    if (len(argv) < 3):
        usage()

    (host, port) = pullPair(argv[1])
    if not port: port = 64738 # default
    (uname, password) = pullPair(argv[2])

    conn = Mumble(host, uname, int(port), password, debug=False)

    # Init behavior through the usage of callbacks.
    conn.callbacks.set_callback(PYMUMBLE_CLBK_CONNECTED,
                                lambda:print("Connection successful!"))
    conn.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED,
                                lambda x:processMessage(x))

    # Connect to server
    print("Connecting...")
    conn.run()
