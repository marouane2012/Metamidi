import mido
import pygame
import time
import sys
import bisect
import threading
from collections import defaultdict
mid = mido.MidiFile('/home/marouane/Music/Beethoven_Virus_Black.mid')
mode = 'play'
showntc = False
pygame.init()
width,height = 1280,800 # 720p
window = pygame.display.set_mode((width,height))
pygame.display.set_caption('Metamidi')
white = (255,255,255)
black = (0,0,0)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)
yellow = (255,255,0)
pink = (255,0,255)
cyan = (0,255,255) # 3 bit colors
grey = (127,127,127)
clock = pygame.time.Clock()
PPQN = mid.ticks_per_beat
print(PPQN)
zoom = 1
offset = 0
colorstable = [red,green,blue,yellow,pink,cyan]
ntc = 0
def miditoabs(f):
    global ntc
    maxnoteticks = 0
    notes = []
    active = defaultdict(list)
    tempoMap = []
    t = 0
    tUs = 0
    cTempo = 500000
    PPQN = f.ticks_per_beat
    tempoMap.append((0,0,500000))
    for track in f.tracks:
        t = 0
        for msg in track:
            tUs += (msg.time/PPQN)*cTempo
            t += msg.time
            if msg.type == 'set_tempo':
                cTempo = msg.tempo
                if t==0:
                    tempoMap[0] = (0,0,cTempo)
                else:
                    tempoMap.append((t,tUs,cTempo))
            elif msg.type == 'note_on':
                active[msg.note].append((t,msg))
            elif msg.type == 'note_off':
                if active[msg.note]:
                    start,omsg = active[msg.note].pop(0)
                    notes.append((start,t,omsg))
                    if t-start > maxnoteticks:
                        maxnoteticks = t-start
    ntc = len(notes)
    notes.sort(key=lambda x:x[0])
    return notes,tempoMap,maxnoteticks
ctick = 0.0
playing = False
lock = threading.Lock()
your_synth = mido.get_output_names()[2] #Change this.
def audio(notes,tempoMap,PPQN):
    global ctick,playing
    out = mido.open_output(your_synth)
    last = time.perf_counter()
    noteIndex = 0
    activeNotes = []
    cTempo = tempoMap[0][2]
    TPS = (1000000/cTempo)*PPQN
    while True:
        if not playing:
            time.sleep(0.001)
            last = time.perf_counter()
            continue
        now = time.perf_counter()
        dt = now-last
        last=now
        with lock:
            prev = ctick
            ctick += dt*TPS
        while noteIndex < len(notes) and notes[noteIndex][0] <= ctick:
            start, end, msg = notes[noteIndex]
            if start >= prev:
                out.send(mido.Message("note_on",note=msg.note,velocity=msg.velocity,channel = msg.channel))
                activeNotes.append((end,msg))
            noteIndex += 1
        still = []
        for end,msg in activeNotes:
            if prev < end <= ctick:
                out.send(mido.Message("note_off",note=msg.note,velocity=0,channel = msg.channel))
            else:
                still.append((end,msg))
        activeNotes = still
        time.sleep(0.001)
def draw(notes,ct,maxnoteticks):
    sticks = 800/zoom
    sstart = ct-(maxnoteticks+sticks) #sstart = ct-maxnoteticks for performance
    send = ct+(maxnoteticks+sticks) #send = ct+maxnoteticks for performance
    idxstart = bisect.bisect_left(notes,(sstart,))
    idxend = bisect.bisect_right(notes,(send,))
    for i in range(idxstart,idxend):
        start,end,note = notes[i]
        tfns = start-ct
        tfne = end-ct
        ys = 720-tfns*zoom
        ye = 720-tfne*zoom
        height = ys-ye
        if ye+height >= 0 and ys-height <= 800:
            color = colorstable[note.channel%len(colorstable)]
            pygame.draw.rect(window,color,(note.note*10,ye,10,height))
def drawpiano():
    for i in range(128):
        if i%12 in (1,3,6,8,10):
            color = black
        else:
            color = white
        pygame.draw.rect(window,color,(10*i,720,10,80))
pt = time.perf_counter()
absmidi,tmap,mnt = miditoabs(mid)
t = threading.Thread(target=audio,args=(absmidi,tmap,mid.ticks_per_beat))
t.start()
font = pygame.font.Font(None,48)
notecount = font.render(str(ntc) + ' notes',None,white)
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            playing = not playing
    with lock:
        ct = ctick
    nt = time.perf_counter()
    dt = (nt - pt)
    pt = nt
    window.fill(black)
    draw(absmidi,ct,mnt)
    drawpiano()
    if showntc:
        window.blit(notecount,(20,20))
    pygame.display.flip()
    clock.tick(60)
