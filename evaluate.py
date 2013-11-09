#!/usr/bin/env python3

import os
import loader
from utils import Dict

# Freimu targetu novērtēšana:
# - gold freimu target saskaitīšana
# - silver freimu targetu saskaitīšana
# - gold un silver sakrītošo freimu targetu saskaitīšana
#
# Freimu elementu novērtēšana:
# - ņem tikai freimus, kuriem sakrīt targeti
# - ar freima elementiem tālāk identiski kā ar targetiem

goldDir = 'gold'
silverDir = 'silver'

goldFrameCount = 0
silverFrameCount = 0
correctFrameCount = 0

goldElementCount = 0
silverElementCount = 0
correctElementCount = 0

paths = list(set(os.path.relpath(path, goldDir) for path in loader.pathIterator2(goldDir))
    & set(os.path.relpath(path, silverDir) for path in loader.pathIterator2(silverDir)))

# for goldPath in loader.pathIterator2(goldDir):
#     relpath = os.path.relpath(goldPath, goldDir)
#     silverPath = os.path.join(silverDir, relpath)
for path in paths:
    goldPath = os.path.join(goldDir, path)
    silverPath = os.path.join(silverDir, path)

    if not os.path.isfile(goldPath) or not os.path.isfile(silverPath):
        continue

    goldDocument = loader.loadDocument(goldPath)
    silverDocument = loader.loadDocument(silverPath)

    # quick cleanup: remove frames without elements and elements without tokenIndex > 0
    for sentence in goldDocument.sentences:
        for frame in sentence.frames:
            frame.elements = [element for element in frame.elements if element.tokenIndex]
        # sentence.frames = [frame for frame in sentence.frames if frame.tokenIndex and len(frame.elements) > 0]
    # tas pats ar silver
    for sentence in silverDocument.sentences:
        for frame in sentence.frames:
            frame.elements = [element for element in frame.elements if element.tokenIndex]
        # sentence.frames = [frame for frame in sentence.frames if frame.tokenIndex and len(frame.elements) > 0]

    # print(goldPath, silverPath)
    # print(relpath)
    print(path)


    for goldSentence, silverSentence in zip(goldDocument.sentences, silverDocument.sentences):

        # if goldSentence.text != silverSentence.text:
        #     print('WARNING, gold and silver sentences differ')

        # šobrīd nav situācijas, kur uz vienu tokenu ir vairāki vienādi freimi

        # freimu skaiti
        goldFrameCount += len(goldSentence.frames)
        silverFrameCount += len(silverSentence.frames)

        # sakrītošo freimu meklēšana

        matchedFrames = []

        silverFrames = list(silverSentence.frames)
        for goldFrame in goldSentence.frames:
            matchedSilverFrame = None
            for silverFrame in silverFrames: 
                if silverFrame.tokenIndex == goldFrame.tokenIndex and silverFrame.type == goldFrame.type:
                    matchedSilverFrame = silverFrame
                    matchedFrames.append([goldFrame, silverFrame])
                    correctFrameCount += 1
                    break
            if matchedSilverFrame:
                silverFrames.remove(matchedSilverFrame)
        

        # salīdzina freimu elementus (tikai sakrītošiem freimiem)

        for goldFrame, silverFrame in matchedFrames:

            goldElementCount += len(goldFrame.elements)
            silverElementCount += len(silverFrame.elements)

            silverElements = list(silverFrame.elements)
            for goldElement in goldFrame.elements:
                matchedSilverElement = None
                for silverElement in silverElements: 
                    if silverElement.tokenIndex == goldElement.tokenIndex and silverElement.name == goldElement.name:
                        matchedSilverElement = silverElement
                        correctElementCount += 1
                        break
                if matchedSilverElement:
                    silverElements.remove(matchedSilverElement)



print()

print('Gold Frame Count =', goldFrameCount)
print('Silver Frame Count =', silverFrameCount)
print('Correct Frame Count =', correctFrameCount)

print()

print('Frame Precision = %.01f%%' % (correctFrameCount / silverFrameCount * 100,))
print('Frame Recall = %.01f%%' % (correctFrameCount / goldFrameCount * 100,))
print('Frame F1 = %.01f%%' % (2 * correctFrameCount / (goldFrameCount + silverFrameCount) * 100,))

print()

print('Gold Element Count =', goldElementCount)
print('Silver Element Count =', silverElementCount)
print('Correct Element Count =', correctElementCount)

print()

print('Element Precision = %.01f%%' % (correctElementCount / silverElementCount * 100,))
print('Element Recall = %.01f%%' % (correctElementCount / goldElementCount * 100,))
print('Element F1 = %.01f%%' % (2 * correctElementCount / (goldElementCount + silverElementCount) * 100,))

print()




