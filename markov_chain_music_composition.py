from mido import MidiFile
import re
import time
import pygame.midi
import random
import threading
import os

pygame.midi.init()
player = pygame.midi.Output(0)
player.set_instrument(0)

# main function for parsing input and starting the program
def main():

    sign = input("Choose the mode (org, 0, 1, 2, 3): ")

    files = os.listdir('./src')
    melodies = {}
    for i in range(len(files)):
        melodies[i+1] = files[i]

    print("Available melodies:")

    for melody in melodies:
        print(f'({melody}) {melodies[melody]}')

    if sign not in ['org', '0', '1', '2', '3']:
        print("Mode not supported!")
        exit()

    mel = int(input("Choose a melody: "))

    if mel not in melodies:
        print("Melody not available!")
        exit()

    mel = f'./src/{melodies[mel]}'

    notes = parseInput(mel)
    simulatenousEvents = distinguishSimultaneousEvents(notes)
    
    if sign == 'org':
        playOriginalMelody(notes)
    
    if sign == '0':
        zeroOrderCompositionMatrix, zeroOrderWaitTime = zeroOrderComposition(simulatenousEvents)
        zeroOrderPlay(zeroOrderCompositionMatrix, zeroOrderWaitTime)

    if sign == '1':
        firstOrderStart, firstOrderCompositionMatrix = firstOrderComposition(simulatenousEvents)
        firstOrderPlay(firstOrderStart, firstOrderCompositionMatrix)

    if sign in ['1', '2', '3']:
        sign = int(sign)
        higherOrderStart, higherOrderCompositionMatrix = higherOrderComposition(sign, simulatenousEvents)
        higherOrderPlay(higherOrderStart, higherOrderCompositionMatrix)

# function for playing a single note
def playNote(note):

    global player

    noteDuration = note[0]
    note = note[1:]

    plays = []
    currNote = []

    for i in range(len(note)):
        currNote.append(note[i])
        if i % 2 == 1:
            plays.append(currNote)
            currNote = []

    for p in plays:
        player.note_on(p[0], p[1])

    time.sleep(noteDuration)

    for p in plays:
        player.note_off(p[0], p[1])

# function for parsing the given midi file
def parseInput(mel):

    list = []
    for msg in MidiFile(mel):
        list.append(str(msg))

    noteList = []

    pattern = re.compile(r'note_(on|off) channel=(\d+) note=(\d+) velocity=(\d+) time=(\d+.*\d*)')
    for x in list:
        z = re.match(pattern, x)
        if z:         
            noteList.append(z.groups())

    notes = []
    for x in noteList:
        notes.append([x[0], int(x[2]), int(x[3]), float(x[4])])

    return notes

# function for playing the original midi file
def playOriginalMelody(notes):

    for note in notes:
        
        time.sleep(note[3])
        
        if note[0] == "on":
            player.note_on(note[1], note[2])

        else:
            player.note_off(note[1], note[2])

# function for distinguishing different notes happening at the same time and grouping them into one atomar event
def distinguishSimultaneousEvents(notes):
    
    simultaneousEvents = []

    atomarEvent = (0, [])

    for note in notes:
        
        if note[3] == 0:
            atomarEvent[1].append((note[0], note[1], note[2]))

        else:
            simultaneousEvents.append(atomarEvent)
            atomarEvent = (note[3], [])
            atomarEvent[1].append((note[0], note[1], note[2]))

    distuinguishedEvents = []

    for e in simultaneousEvents:
        onOffs = [x[0] for x in e[1]]

        if 'on' in onOffs and 'off' in onOffs:
            eventOn = (0, [])
            eventOff = (e[0], [])
            for i in e[1]:
                if i[0] == "on":
                    eventOn[1].append(i)
                else:
                    eventOff[1].append(i)
            distuinguishedEvents.append(eventOff)
            distuinguishedEvents.append(eventOn)

        else:
            distuinguishedEvents.append(e)

    for e in distuinguishedEvents:
        e[1].sort()

    return distuinguishedEvents

# function which generates Markov chain in which all notes are random and equally distributed
def zeroOrderComposition(events):

    plays = []

    for i in range(len(events)):

        e = events[i][1]
        
        if e[0][0] == 'on':

            notes = [x[1] for x in e]
            noteVelocity = {}
            for x in e:
                noteVelocity[x[1]] = x[2]

            unmatched = set(notes.copy())
            matched = set()
            duration = 0

            for j in range(i+1, len(events)):
                duration += events[j][0]
                if events[j][1][0][0] == 'off':
                    offNotes = [x[1] for x in events[j][1]]
                    if len(set(offNotes).intersection(set(unmatched))) > 0:
                        newlyFound = []
                        for el in offNotes:
                            if el in unmatched:
                                matched.add(el)
                                unmatched.remove(el)
                                newlyFound.append((el, noteVelocity[el]))
                        if len(newlyFound) > 0:
                            newlyFound.sort()
                            plays.append((duration, newlyFound))
                if len(unmatched) == 0:
                    break

    hashableList = []
    for p in plays:
        l = []
        l.append(p[0])
        for i in p[1]:
            l.append(i[0])
            l.append(i[1])
        hashableList.append(tuple(l))

    occurences = {}
    for el in hashableList:
        if el not in occurences:
            occurences[el] = 1
        else:
            occurences[el] = occurences[el] + 1

    t = 0
    transitionDict = {}
    for el in occurences:
        t += occurences[el]
        transitionDict[t] = el

    currTime = 0
    waitDict = {}
    for i in range(len(events)):
        currEvent = events[i]
        currTime += currEvent[0]
        if currEvent[1][0][0] == 'on' and currTime != 0:
            if currTime not in waitDict:
                waitDict[currTime] = 1
            else:
                waitDict[currTime] = waitDict[currTime] + 1
            currTime = 0

    t = 0
    timeDict = {}
    for el in waitDict:
        t += waitDict[el]
        timeDict[t] = el

    return transitionDict, timeDict

# function for generating music using given zero order Markov chain
def zeroOrderPlay(transition, wait):

    transitionKeys = transition.keys()
    waitKeys = wait.keys()

    transitionMax = max(transitionKeys)
    waitMax = max(waitKeys)
    
    while True:
        
        nextTransitionIndex = random.randint(1, transitionMax)
        waitTime = random.randint(1, waitMax)

        while nextTransitionIndex not in transitionKeys:
            nextTransitionIndex += 1
        
        while waitTime not in waitKeys:
            waitTime += 1

        t = threading.Thread(target = playNote, args = [transition[nextTransitionIndex]])
        t.start()
        time.sleep(wait[waitTime])

# function for creating Markov chain in which the current atomar event depends only on the last
def firstOrderComposition(events):
    
    plays = []

    passedTime = None
    currTime = 0

    for i in range(len(events)):

        e = events[i][1]

        try:
            passedTime += events[i][0]
        except:
            pass
        
        if e[0][0] == 'on':

            if passedTime == None:
                passedTime = 0

            else:
                currTime = passedTime
                passedTime = 0

            notes = [x[1] for x in e]
            noteVelocity = {}
            for x in e:
                noteVelocity[x[1]] = x[2]

            unmatched = set(notes.copy())
            matched = set()
            duration = 0

            for j in range(i+1, len(events)):
                duration += events[j][0]
                if events[j][1][0][0] == 'off':
                    offNotes = [x[1] for x in events[j][1]]
                    if len(set(offNotes).intersection(set(unmatched))) > 0:
                        newlyFound = []
                        for el in offNotes:
                            if el in unmatched:
                                matched.add(el)
                                unmatched.remove(el)
                                newlyFound.append((el, noteVelocity[el]))
                        if len(newlyFound) > 0:
                            newlyFound.sort()
                            plays.append((duration, newlyFound, currTime))
                if len(unmatched) == 0:
                    break

    hashableList = []
    for p in plays:
        l = []
        l.append(p[0])
        for i in p[1]:
            l.append(i[0])
            l.append(i[1])
        l.append(p[2])
        hashableList.append(tuple(l))

    transitionDict = {}
    start = None

    for i in range(len(hashableList)):
        if i > 0:
            prev = hashableList[i-1]
            prev = prev[:len(prev)-1]
        else:
            prev = None
        curr = hashableList[i]
        
        if prev == None:
            start = curr

        else:

            if prev == None:
                continue
            
            if prev not in transitionDict:
                transitionDict[prev] = [curr]

            else:
                transitionDict[prev].append(curr)

    return start, transitionDict

# function for generating music using given first order Markov chain
def firstOrderPlay(curr, matrix):

    start = curr[:len(curr)-1]

    curr = curr[:len(curr)-1]

    while True:

        try:
            candidates = matrix[curr[:len(curr)]]
        except:
            curr = start
            candidates = matrix[curr[:len(curr)]]
        
        t = threading.Thread(target = playNote, args = [curr])
        t.start()

        next = random.choice(candidates)
        timeToSleep = next[len(next)-1]
        curr = next[:len(next)-1]

        time.sleep(timeToSleep)

# function for creating Markov chain in which the current atomar event depends only on 'order' amount of last events
def higherOrderComposition(order, events):
    
    plays = []

    passedTime = None
    currTime = 0

    for i in range(len(events)):

        e = events[i][1]

        try:
            passedTime += events[i][0]
        except:
            pass
        
        if e[0][0] == 'on':

            if passedTime == None:
                passedTime = 0

            else:
                currTime = passedTime
                passedTime = 0

            notes = [x[1] for x in e]
            noteVelocity = {}
            for x in e:
                noteVelocity[x[1]] = x[2]

            unmatched = set(notes.copy())
            matched = set()
            duration = 0

            for j in range(i+1, len(events)):
                duration += events[j][0]
                if events[j][1][0][0] == 'off':
                    offNotes = [x[1] for x in events[j][1]]
                    if len(set(offNotes).intersection(set(unmatched))) > 0:
                        newlyFound = []
                        for el in offNotes:
                            if el in unmatched:
                                matched.add(el)
                                unmatched.remove(el)
                                newlyFound.append((el, noteVelocity[el]))
                        if len(newlyFound) > 0:
                            newlyFound.sort()
                            plays.append((duration, newlyFound, currTime))
                if len(unmatched) == 0:
                    break

    hashableList = []
    for p in plays:
        l = []
        l.append(p[0])
        for i in p[1]:
            l.append(i[0])
            l.append(i[1])
        l.append(p[2])
        hashableList.append(tuple(l))

    currPlay = []
    actualPlays = []

    j = 0
    while len(currPlay) < order:
        currPlay.append(hashableList[j])
        j += 1

    actualPlays.append(currPlay.copy())

    for i in range(j, len(hashableList)):
        currPlay.pop(0)
        currPlay.append(hashableList[i])
        actualPlays.append(currPlay.copy())

    keys = []
    for play in actualPlays:
        keys.append('|'.join([str(x) for x in play]))

    transitionDict = {}
    start = None

    for i in range(len(keys)):

        if i > 0:
            prev = keys[i-1]
        else:
            prev = None

        curr = keys[i]

        if prev == None:
            start = curr

        else:

            if prev not in transitionDict:
                transitionDict[prev] = [curr]

            else:
                transitionDict[prev].append(curr)

    return start, transitionDict

# function for generating music using given higher order Markov chain
def higherOrderPlay(curr, matrix):
    
    start = eval(curr.split('|')[0])
    start = start[:len(start)-1]

    currNote = start

    while True:

        try:
            candidates = matrix[curr]
        except:
            curr = start
            candidates = matrix[curr]

        print(curr)
        
        t = threading.Thread(target = playNote, args = [currNote])
        t.start()

        next = random.choice(candidates)
        nextNote = eval(next.split('|')[0])
        timeToSleep = nextNote[len(nextNote)-1]
        nextNote = nextNote[:len(nextNote)-1]

        curr = next
        currNote = nextNote

        time.sleep(timeToSleep)

main()
