import argparse
import pathlib
import mido
import tqdm
import json
import time
from pynput.keyboard import Key, Controller


def get_key_map():
    init_map = {

        36: ["z"],
        37: ["shift", "z"],
        38: ["x"],
        39: ["ctrl", "c"],
        40: ["c"],
        41: ["v"],
        42: ["shift", "v"],
        43: ["b"],
        44: ["shift", "b"],
        45: ["n"],
        46: ["ctrl", "m"],
        47: ["m"],

        48: ["a"],
        49: ["shift","a"],
        50: ["s"],
        51: ["ctrl", "d"],
        52: ["d"],
        53: ["f"],
        54: ["shift", "f"],
        55: ["g"],
        56: ["shift", "g"],
        57: ["h"],
        58: ["ctrl", "j"],
        59: ["j"],

        60: ["q"], # middle c
        61: ["shift", "q"],
        62: ["w"],
        63: ["ctrl", "e"],
        64: ["e"],
        65: ["r"],
        66: ["shift", "r"],
        67: ["t"],
        68: ["shift", "t"],
        69: ["y"],
        70: ["ctrl", "u"],
        71: ["u"]


    }

    for note in range(72, 128): 

        init_map[note] = init_map[60 + (note % 12)]
    for note in range(36):
        init_map[note] = init_map[36 + (note % 12)]


    return init_map



def search_track(tracks, name):
    for track in tracks:
        track_name = str(track).split('\\')[1]
        if name.lower() in track_name.lower():
            return str(track)
    raise ValueError("Track does not exist!")


def press_keys(keys, keyboard):
    for key in keys:
        if len(key) == 1:
            keyboard.press(key)
            keyboard.release(key)
        elif key == "shift":
            keyboard.press(Key.shift)
            
        elif key == "ctrl":
            keyboard.press(Key.ctrl)
            
        else:
            raise NotImplementedError()
    # resolves issue with wwm's keys
    keyboard.release(Key.shift)
    keyboard.release(Key.ctrl)


def play_track(track_path, key_map, min_velocity = 0):
    keyboard = Controller()
    mid = mido.MidiFile(track_path)
    for msg in mid:
        time.sleep(msg.time)
        if msg.type == "note_on" and msg.velocity > min_velocity:
            press_keys(key_map[msg.note], keyboard)
        elif msg.type == "note_off":
            ...
            # asume we dont need to release
            # release_keys(key_map[msg.note])


def transpose_track(track_path, num, auto=True):

    # do the transpose to a key stated by num
    above_sixty = 0
    below_thirty_six = 0
    total_notes = 0
    mid = mido.MidiFile(track_path, clip=True)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' or msg.type == 'note_off':
                
                new_note = msg.note + num

                # heuristic
                if msg.type == 'note_on':
                    total_notes += 1
                
                # balancing
                if new_note < 0:
                    new_note = new_note % 12
                elif new_note > 127:
                    new_note = new_note % 12 + 120 # C9
                msg.note = new_note
                if msg.note >= 60:
                    above_sixty += 1
                elif msg.note < 36:
                    below_thirty_six += 1

    if auto:
    # fix extreme notes and shift octaves
        while above_sixty/total_notes >= 0.7:
            above_sixty = 0
            below_thirty_six = 0
            total_notes = 0
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'note_on' or msg.type == 'note_off':
                        new_note = msg.note - 12
                        if msg.type == 'note_on':
                            total_notes += 1
                        
                        if new_note < 0:
                            new_note = new_note % 12
                        msg.note = new_note
                        if msg.note >= 60:
                            above_sixty += 1
                        elif msg.note < 36:
                            below_thirty_six += 1


        while below_thirty_six/total_notes >= 0.8 or above_sixty/total_notes < 0.35:
            above_sixty = 0
            below_thirty_six = 0
            total_notes = 0
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'note_on' or msg.type == 'note_off':
                        new_note = msg.note + 12
                        if msg.type == 'note_on':
                            total_notes += 1
                        
                        if new_note > 128:
                            new_note = new_note % 12 + 60
                        msg.note = new_note
                        if msg.note >= 60:
                            above_sixty += 1
                        elif msg.note < 36:
                            below_thirty_six += 1
                    
                    
    final_name = "tracks/" + track_path.split("\\")[1]
    mid.save(final_name)
    return final_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-t", "--transpose", type=int, default=0)
    parser.add_argument("-mt", "--manual_transpose", action="store_true")
    parser.add_argument("-ft", "--force_transpose", action="store_true")
    args = parser.parse_args()
    # print("hi")
    if not args.force_transpose:
        path = pathlib.Path("./tracks")
        tracks = list(path.glob("*.mid"))

        selected_track = search_track(tracks, args.file.lower())
        time.sleep(2)
        print("lets go!")
        play_track(selected_track, get_key_map())
        
    else:
        manual = args.manual_transpose
        path = pathlib.Path("./raw_tracks")
        tracks = list(path.glob("*.mid"))
        selected_track = search_track(tracks, args.file.lower())
        transposed_track = transpose_track(selected_track, args.transpose, auto=(not manual))
        play_track(transposed_track, get_key_map())

