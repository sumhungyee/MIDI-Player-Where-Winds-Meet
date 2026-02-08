
import altair as alt
import pathlib
import mido
import tqdm
import json
import os
import pandas as pd
import time
import streamlit as st
import json
import pyautogui


from threading import Thread, Event
from pynput.keyboard import Key, Controller

WWM_UB = 71
WWM_LB = 36
st.title("Midi Player for Where Winds Meet")
st.html("button_style.html",unsafe_allow_javascript=True)

if 'pause_event' not in st.session_state:
    st.session_state['pause_event'] = Event()
if 'stop_event' not in st.session_state:
    st.session_state['stop_event'] = Event()
if 'loop' not in st.session_state:
    st.session_state['loop'] = 0 
if 'current_track' not in st.session_state:
    st.session_state['current_track'] = ""
    # 0 for no loop,
    # 1 for repeat current track
    # 2 for loop in order
    # 3 for shuffle

os.makedirs("/tracks", exist_ok = True)
os.makedirs("/raw_tracks", exist_ok = True)

@st.cache_data
def get_key_map():

    init_map = {

        WWM_LB: ["z"],
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
        WWM_UB: ["u"]
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
    if pyautogui.getActiveWindowTitle() != "Where Winds Meet":
        return
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


def play_track(track_path, key_map, stop_event, min_velocity = 0):
    keyboard = Controller()
    mid = mido.MidiFile(track_path)
    for msg in mid:
        
        time.sleep(msg.time)
        if msg.type == "note_on" and msg.velocity > min_velocity:
            press_keys(key_map[msg.note], keyboard)
        
        # asume we dont need to release
        # elif msg.type == "note_off":
            # release_keys(key_map[msg.note])
        if stop_event.is_set():
            break

def play_track_repeat(track_path, key_map, stop_event, min_velocity = 0):

    mid = mido.MidiFile(track_path)
    while not stop_event.is_set():
        play_track(track_path, key_map, stop_event, min_velocity = min_velocity)
        time.sleep(2)

def play_album(track_path, key_map, stop_event, min_velocity = 0):
    iteration = 0

    while not stop_event.is_set():
        if iteration == 0:
            play_track(track_path, key_map, stop_event, min_velocity = min_velocity)
        else:
            path = list(pathlib.Path("./tracks").iterdir())
            total_len = len(path)
            idx = (path.index(track_path) + 1) % total_len
            track_path = path[idx]

            play_track(track_path, key_map, stop_event, min_velocity = min_velocity)
        iteration += 1
        time.sleep(2)

def play_album_random(track_path, key_map, stop_event, min_velocity = 0):
    import random
    curr_track_path = track_path
    while not stop_event.is_set():
        
        play_track(curr_track_path, key_map, stop_event, min_velocity = min_velocity)
        path = list(pathlib.Path("./tracks").iterdir())
        path.remove(curr_track_path)
        curr_track_path = random.choice(path)
        time.sleep(2)
        

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
                    
                    
    final_name = "tracks/" + str(track_path).split("\\")[1]
    mid.save(final_name)
    return final_name


force_transpose = st.toggle("Transpose Raw Track")
manual = False

if force_transpose:
    manual = st.toggle("Manually Transpose Track")
    path = pathlib.Path("./raw_tracks")
    transpose_amount = 0
    if manual:
        transpose_amount = st.number_input("Transpose Amount (Semitones)", value=0, step=1)
        if abs(transpose_amount) > 128:
            st.warning("Warning: Maximum Midi range is $0$ to $128$!")
else:
    path = pathlib.Path("./tracks")
tracks = list(path.glob("*.mid"))
selected_track = st.selectbox("Select Track", tracks)




def update_curr_track(curr_playing):
    with curr_playing:
        if isinstance(st.session_state['current_track'], str):
            st.markdown(
                f'<div style="text-align: center;  font-family: monospace;">Playing: {
                str(st.session_state['current_track'])
                }</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div style="text-align: center;  font-family: monospace;">Playing: {
                str(st.session_state['current_track']).split("\\")[-1]
                }</div>', unsafe_allow_html=True)


def loop_callback():
    st.session_state["loop"] = (st.session_state["loop"] + 1) % 4

curr_playing = st.empty()


with st.expander(label="Track Analysis"):
    analyse = st.button("Analyse Track", width=900, type="primary")
    
    if analyse:
        with st.spinner("Loading...", show_time=True):
            mid = mido.MidiFile(selected_track)
            num_notes = len(list(mid))
            
            current_time = 0
            notes_time = []

            for msg in mid:
                current_time += msg.time 
                if msg.type == 'note_on':
                    notes_time.append((msg.note, current_time, msg.velocity))

            note_label = "Original MIDI Note"
            time_label = "Time (s)"
            df = pd.DataFrame(notes_time, columns=[note_label, time_label, "velocity"])
            points = alt.Chart(df).mark_circle(size=60).encode(
                    x=f'{time_label}:Q',  
                    y=f'{note_label}:Q',  
                    color=alt.Color('velocity:Q', scale=alt.Scale(scheme='magma')) 
            )
            rule1 = alt.Chart(pd.DataFrame({note_label: [WWM_UB]})).mark_rule(
                color='red', 
                strokeWidth=2,
                strokeDash=[5, 5]
            ).encode(
                y=f'{note_label}:Q'
            )

            rule2 = alt.Chart(pd.DataFrame({note_label: [WWM_LB]})).mark_rule(
                color='red', 
                strokeWidth=2,
                strokeDash=[5, 5]
            ).encode(
                y=f'{note_label}:Q'
            )

            final_chart = (points + rule1 + rule2).properties(
                title="MIDI Note Distribution"
            ).interactive()
            st.altair_chart(final_chart, width="stretch")
            st.info(
                """The dotted red lines demarcate the upper \
                    and lower bounds of the Where Winds Meet keyboard, which spans 3 octaves.""",
                    icon="ℹ️"
                )

_, _, _, col1, col2, col3, _, _, _ = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1])
with col1:
    play = st.button("▶", type="primary", key="start")
with col2:
    stop = st.button("■", type="secondary", key="stop")
with col3:
    if st.session_state["loop"] == 0:
        icon = "🎵"
    elif st.session_state["loop"] == 1:
        icon = "🔂"
    elif st.session_state["loop"] == 2:
        icon = "🔁"
    else:
        icon = "🔀"

    looper = st.button(
        icon, 
        type="tertiary", 
        key="looper",
        on_click=loop_callback,
        disabled=force_transpose
    )



if play:
    w = pyautogui.getWindowsWithTitle("Where Winds Meet")
    if not w:
        raise ValueError("Where Winds Meet not Detected")
    try:
        w[0].activate()
    except:
        st.warning("Could not maximise Where Winds Meet!")

    


    st.session_state['stop_event'].set() # stop any running processes first
    if 'process' in st.session_state and st.session_state['process'] is not None:
        st.session_state['process'].join()
    st.session_state['stop_event'].clear()
    
    # main idea
    if force_transpose:
        st.session_state['current_track'] = selected_track
        update_curr_track(curr_playing)

        transposed_track = transpose_track(selected_track, transpose_amount, auto=(not manual))
        st.session_state["process"] = Thread(
            target=play_track, 
            args=(transposed_track, get_key_map(), st.session_state['stop_event'])
        )
        
    elif st.session_state['loop'] == 0:
        st.session_state['current_track'] = selected_track
        update_curr_track(curr_playing)


        st.session_state["process"] = Thread(
            target=play_track, 
            args=(selected_track, get_key_map(), st.session_state['stop_event'])
        )
    elif st.session_state['loop'] == 1:
        st.session_state['current_track'] = selected_track
        update_curr_track(curr_playing)


        st.session_state["process"] = Thread(
            target=play_track_repeat, 
            args=(selected_track, get_key_map(), st.session_state['stop_event'])
        )
    elif st.session_state['loop'] == 2:
        st.session_state['current_track'] = "All Tracks"
        update_curr_track(curr_playing)

        
        st.session_state["process"] = Thread(
            target=play_album, 
            args=(selected_track, get_key_map(), st.session_state['stop_event'])
        )
    else:
        raise NotImplementedError()
    
    st.session_state["process"].daemon = True
    st.session_state["process"].start()

if stop and 'process' in st.session_state and st.session_state['process'] is not None:
    st.session_state["stop_event"].set()
    st.session_state['process'].join()
    st.session_state["stop_event"].clear()


