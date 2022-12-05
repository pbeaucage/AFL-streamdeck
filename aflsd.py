#!/usr/bin/env python3

#         Python Stream Deck Library
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

# Example script showing basic library usage - updating key images with new
# tiles generated at runtime, and responding to button state change events.

import os
import threading
import random
import time
import AFL.automation 

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.Transport.Transport import TransportError



# Folder location of image assets used by this example.
ASSETS_PATH = os.curdir + '/SD_Imgs/'


# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
def render_key_image(deck, key_style): #dict containing icon_filename, font_filename, label_text,icon_text):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.
    if key_style['icon'] != '':
        icon = Image.open(key_style['icon'])
        image = PILHelper.create_scaled_image(deck, icon, margins=[0, 0, 20, 0])
    else:
        image = PILHelper.create_image(deck,background='black')
        
    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image a few pixels from the bottom of the key.
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(key_style['font'], 14)
    icon_font = ImageFont.truetype(key_style['icon_font'],32) #this must be one of only a few valid sizes for an emoji font: https://github.com/python-pillow/Pillow/issues/1422
    
    try:
        draw.text((image.width / 2, image.height/2), text=key_style['icon_text'], font=icon_font, anchor="ms",fill=key_style['icon_color'])#,embedded_color=True)# test , fill="white")
    except KeyError:
        pass
    label_draw_offset = key_style['label'].count('\n')*10+8
    draw.text((image.width / 2, image.height - label_draw_offset), text=key_style['label'], font=font, anchor="ms", fill="white")

    return PILHelper.to_native_format(deck, image)

# Returns styling information for a key based on its position and state.
def get_key_style(deck, key, state):
    try:
        keyconfig = keydata[key]
    except KeyError:
        keyconfig = {'name':'','appearance':{'icon':'','font':'','label':'','icon_text':'','icon_font':'','icon_color':'white'},'action':''}
    
    if keyconfig['action'] == 'toggle':
        if deck._AFL_toggle_state[key]:
            keyconfig['appearance'] = keyconfig['on_appearance']
        else:
            keyconfig['appearance'] = keyconfig['off_appearance']
    try:
        if keyconfig['status_type'] == 'state':
            state = keyconfig['status_callback'](deck,key,state)
            keyconfig['appearance'] = keyconfig[f'{state}_appearance']
        elif keyconfig['status_type'] == 'numeric':
            status_num = keyconfig['status_callback'](deck,key,state)
            keyconfig['appearance']['icon_text'] = str(status_num)
    except KeyError:
        pass
    keyconfig.update(keyconfig['appearance'])
    
    try:
        keyconfig['icon_color']
    except KeyError:
        keyconfig['icon_color'] = 'white'
    
    try:
        if keyconfig['icon'] != '':
            keyconfig['icon'] = os.path.join(ASSETS_PATH,keyconfig['icon'])
    except KeyError:
        keyconfig['icon'] = ''
    
    if keyconfig['icon_font'] != '':
        keyconfig['icon_font'] = os.path.join(ASSETS_PATH,keyconfig['icon_font'])
    else:
        keyconfig['icon_font'] = os.path.join(ASSETS_PATH,'Apple Color Emoji.ttc')
        
    if keyconfig['font'] != '':
        keyconfig['font'] = os.path.join(ASSETS_PATH,keyconfig['font'])
    else:
        keyconfig['font'] = os.path.join(ASSETS_PATH,'Comic Sans MS.ttf')
                
    return keyconfig


# Creates a new key image based on the key index, style and current key state
# and updates the image on the StreamDeck.
def update_key_image(deck, key, state):
    # Determine what icon and label to use on the generated key.
    key_style = get_key_style(deck, key, state)

    # Generate the custom key with the requested image and label.
    image = render_key_image(deck, key_style)

    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Update requested key with the generated image.
        deck.set_key_image(key, image)


# Prints key state change information, updates rhe key image and performs any
# associated actions when a key is pressed.
def key_change_callback(deck, key, state):
    # Print new key state
    print("Deck {} Key {} = {}".format(deck.id(), key, state), flush=True)

    try:
        data = keydata[key]
        if data['action'] == 'toggle' and not state:
            deck._AFL_toggle_state[key] = not deck._AFL_toggle_state[key]
            toggle_state = deck._AFL_toggle_state[key]
            print(f'Updating toggle state for key {key}, state dict = {deck._AFL_toggle_state}')
        # Update the key image based on the new key state.
        update_key_image(deck, key, state)
        try:
            if data['action'] == 'momentary' and state:
                print(f'{key} state {state} momentary, firing cb')
                data['callback'](deck,key,state)
            elif data['action'] == 'toggle' and not state:
                print(f'{key} state {state} toggle, firing cb')
                data['callback'](deck,key,toggle_state)
            elif data['action'] == 'state_ind':
                print(f'{key} is state indicator, sending pause')
            elif data['action'] != 'momentary' and data['action'] != 'toggle':
                print(f'{key} state {state} catchall, firing cb')
                data['callback'](deck,key,state)
        except KeyError:
            pass
    except KeyError:
        pass
        

def exit_cb(deck,key,state):
    # Use a scoped-with on the deck to ensure we're the only thread
    # using it right now.
    with deck:
        # Reset deck, clearing all button images.
        deck.reset()

        # Close deck handle, terminating internal worker threads.
        deck.close()
def playpause_cb(deck,key,state):
    if state:
        print(f'{key} Paused!')
    else:
        print(f'{key} Running!')
def playpause_cb(deck,key,state):
    if state:
        print(f'{key} Paused!')
    else:
        print(f'{key} Running!')
def dummy_cb(deck,key,state):
    print(f'Dummy cb {key} @ {state}')
def dummy_numeric(deck,key,state):
    return random.randrange(10)


def dummy_state(deck,key,state):
    var = random.randrange(3)
    status = ''
    if var == 0:
        status = 'paused'
    elif var == 1:
        status = 'running'
    elif var == 2:
        status = 'idle'
    return status
def update_status(sleep):
    # Periodic loop that will render every frame at the set FPS until
    # the StreamDeck device we're using is closed.
    while deck.is_open():
        try:
            # Use a scoped-with on the deck to ensure we're the only
            # thread using it right now.
            with deck:
                # Update the key images with the next animation frame.
                for num,key in keydata.items():
                    try:
                        test = key['status_type']
                        update_key_image(deck,num,True)
                    except KeyError:
                        pass
        except TransportError as err:
            print("TransportError: {0}".format(err))
            # Something went wrong while communicating with the device
            # (closed?) - don't re-schedule the next animation frame.
            break
        if sleep >= 0:
            time.sleep(sleep)
def AFL_sd_queued_items(client):
    def cb(deck,key,state):
        try:
            queue = client.get_queue()
            queued = len(queue[2])
        except ConnectionRefusedError:
            queued = -1
        return queued
    return cb 
def AFL_sd_enqueue(client,task_name,**kwargs):
    def cb(deck,key,state):
        try:
            client.enqueue(task_name=task_name,**kwargs)
        except ConnectionRefusedError:
            pass
    return cb 

def AFL_sd_server_status(client):
    def cb(deck,key,state):
        try:
            state = client.queue_state().content.decode('UTF-8')
        except ConnectionRefusedError:
            state = 'Error'
        return state
    return cb
def AFL_sd_toggle_pause(client):
    def cb(deck,key,state):
        if state:
            try:
                state = client.queue_state().content.decode('UTF-8')
                if state == 'Paused':
                    client.pause(False)
                else:
                    client.pause(True)
            except ConnectionRefusedError:
                pass
    return cb
if __name__ == "__main__":
    from AFL.automation.APIServer.Client import Client
    load_client = Client(ip='piloader',port=5000)
    load_client.login('SDStatus')
    
    inst_client = load_client
    robot_client = Client(ip='piot2',port=5000)
    robot_client.login('SDStatus')
    
    keydata = {}

    keydata[14] = {'name':'exit','action':'momentary',
                   'appearance':{'icon':'','font':'Arial.ttf','label':'E-STOP','icon_text':'🛑','icon_font':'','icon_color':'red'},
                   'callback':exit_cb}
    keydata[0] = {'name':'loaderpause','action':'state',\
                  'Paused_appearance':{'icon':'','font':'Arial.ttf','label':'Loader\nPaused','icon_text':'💪▶️','icon_font':'','icon_color':'red'},
                  'Error_appearance':{'icon':'','font':'Arial.ttf','label':'Connection\nError','icon_text':'💪⚠️','icon_font':'','icon_color':'red'},
                  'Active_appearance':{'icon':'','font':'Arial.ttf','label':'Loader\nRunning','icon_text':'💪⏸️','icon_font':'','icon_color':'green'},
                  'Ready_appearance':{'icon':'','font':'Arial.ttf','label':'Loader\nIdle','icon_text':'💪⏸️','icon_font':'','icon_color':'yellow'},
                   'callback':AFL_sd_toggle_pause(load_client),
                   'status_type':'state',
                   'status_callback':AFL_sd_server_status(load_client)
                 }
    keydata[5] = {'name':'instpause','action':'state',
                  'Paused_appearance':{'icon':'','font':'Arial.ttf','label':'Instrument\nPaused','icon_text':'🎸▶️','icon_font':'','icon_color':'red'},
                  'Error_appearance':{'icon':'','font':'Arial.ttf','label':'Connection\nError','icon_text':'🎸⚠️','icon_font':'','icon_color':'red'},
                  'Active_appearance':{'icon':'','font':'Arial.ttf','label':'Instrument\nRunning','icon_text':'🎸⏸️','icon_font':'','icon_color':'green'},
                  'Ready_appearance':{'icon':'','font':'Arial.ttf','label':'Instrument\nIdle','icon_text':'🎸⏸️','icon_font':'','icon_color':'yellow'},
                   'callback':AFL_sd_toggle_pause(inst_client),
                   'status_type':'state',
                   'status_callback':AFL_sd_server_status(inst_client)
             }
    keydata[10] = {'name':'robotpause','action':'state',
                  'Paused_appearance':{'icon':'','font':'Arial.ttf','label':'Robot\nPaused','icon_text':'🤖▶️','icon_font':'','icon_color':'red'},
                  'Error_appearance':{'icon':'','font':'Arial.ttf','label':'Connection\nError','icon_text':'🤖⚠️','icon_font':'','icon_color':'red'},
                  'Active_appearance':{'icon':'','font':'Arial.ttf','label':'Robot\nRunning','icon_text':'🤖⏸️','icon_font':'','icon_color':'green'},
                  'Ready_appearance':{'icon':'','font':'Arial.ttf','label':'Robot\nIdle','icon_text':'🤖⏸️','icon_font':'','icon_color':'yellow'},
                   'callback':AFL_sd_toggle_pause(robot_client),
                   'status_type':'state',
                   'status_callback':AFL_sd_server_status(robot_client)
             }
    
    keydata[2] = {'name':'rinse','action':'momentary',
                   'appearance':{'icon':'','font':'Arial.ttf','label':'RinseCell','icon_text':'💦','icon_font':'','icon_color':'blue'},
                   'callback':dummy_cb}
    keydata[3] = {'name':'load','action':'momentary',
                   'appearance':{'icon':'','font':'Arial.ttf','label':'Load\nSample','icon_text':'➡️','icon_font':'','icon_color':'red'},
                   'callback':dummy_cb}
    
    keydata[4] = {'name':'calibrate','action':'momentary',
                   'appearance':{'icon':'','font':'Arial.ttf','label':'Calibrate\nSensors','icon_text':'📏','icon_font':'','icon_color':'red'},
                   'callback':dummy_cb}
        
    
    keydata[12] = {'name':'refill','action':'momentary',
              'appearance':{'icon':'','font':'Arial.ttf','label':'Refill\nTipracks','icon_text':'💉','icon_font':''},
              'callback':AFL_sd_enqueue(robot_client,'slow_test_function')
             }
    keydata[13] = {'name':'home','action':'momentary',
              'appearance':{'icon':'','font':'Arial.ttf','label':'Home\nRobot','icon_text':'🏠','icon_font':''},
              'callback':dummy_cb
             }
    keydata[1] = {'name':'loaderqueue','action':'momentary',
              'appearance':{'icon':'','font':'Arial.ttf','label':'queued','icon_text':'4','icon_font':'Arial.ttf'},
              'callback':dummy_cb,
              'status_type':'numeric',
              'status_callback':AFL_sd_queued_items(load_client)
             }
    keydata[6] = {'name':'instqueue','action':'momentary',
              'appearance':{'icon':'','font':'Arial.ttf','label':'queued','icon_text':'2','icon_font':'Arial.ttf'},
              'callback':dummy_cb,
              'status_type':'numeric',
              'status_callback':AFL_sd_queued_items(inst_client)
             }
    keydata[11] = {'name':'robotqueue','action':'momentary',
              'appearance':{'icon':'','font':'Arial.ttf','label':'queued','icon_text':'0','icon_font':'Arial.ttf'},
              'callback':dummy_cb,
              'status_type':'numeric',
              'status_callback':AFL_sd_queued_items(robot_client)
             }





    streamdecks = DeviceManager().enumerate()

    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    for index, deck in enumerate(streamdecks):
        deck.open()
        deck.reset()

        print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))

        # Set initial screen brightness to 30%.
        deck.set_brightness(100)

                  
        
        deck._AFL_toggle_state = {}
            
                  
        # Set initial key images.
        for key in range(deck.key_count()):
            try:
                if keydata[key]['action'] == 'toggle':
                  deck._AFL_toggle_state[key] = False
            except:
                pass
            
            update_key_image(deck, key, False)
        # Register callback function for when a key state changes.
        deck.set_key_callback(key_change_callback)
        threading.Thread(target=update_status, args=[0.2]).start()
        # Wait until all application threads have terminated (for this example,
        # this is when all deck handles are closed).
        for t in threading.enumerate():
            try:
                t.join()
            except RuntimeError:
                pass


