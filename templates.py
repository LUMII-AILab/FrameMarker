#!/usr/bin/env python3


header = """#!/usr/bin/env python3

from %s import frameTargetFeatures, frameElementFeatures
from utils import Dict


"""

allElements = """

# all element names
frameElementNames = set()
for frameType, elementNames in frameTypesWithElementNames.items():
    frameElementNames |= elementNames


"""

main = """

def getFrames(tokens):

    frames = []

    for frameType in frameTypesWithElementNames:
        function = frameTypeFunctions[frameType]

        for token in tokens:
            # rules = function(forClassName="YES", **frameTargetFeatures(token=token, tokens=tokens))
            rules = function(**frameTargetFeatures(token=token, tokens=tokens))
            # ir nostrādājis vismaz viens YES likums
            if rules:
                if type(rules) != list and type(rules) != tuple:
                    rules = None
                frames.append(Dict(type=frameType, tokenIndex=token.index, elements=[], rules=rules))

    return frames



def getFrameElements(tokens, frames, maxdist=3):

    frameTargetIndicesByElementNames = {}

    # sagrupē freimu targetus pēc elementu nosaukumiem
    for frame in frames:
        for elementName in frameTypesWithElementNames[frame.type]:

            function = frameElementFunctions[elementName]

            for token in tokens:
                # rules = function(forClassName="YES", **frameElementFeatures(token=token, tokens=tokens, elementName=elementName, frame=frame))
                rules = function(**frameElementFeatures(token=token, tokens=tokens, elementName=elementName, frame=frame))

                # ok, pozitīvs, bet kā sagrupēs ?
                if rules:
                    if type(rules) != list and type(rules) != tuple:
                        rules = None

                    # frame.elements.append(Dict(tokenIndex=token.index, name=elementName, rules=rules))
                    if not tokens[frame.tokenIndex].distances or token.index == frame.tokenIndex or len(tokens[frame.tokenIndex].distances[token.index]) <= maxdist:
                        frame.elements.append(Dict(tokenIndex=token.index, name=elementName, rules=rules))

"""

oldmain = """
def getFrameElements(tokens, frames):

    frameTargetIndicesByElementNames = {}

    # sagrupē freimu targetus pēc elementu nosaukumiem
    for frame in frames:
        for elementName in frameTypesWithElementNames[frame.type]:
            if elementName not in frameTargetIndicesByElementNames:
                frameTargetIndicesByElementNames[elementName] = set()
            frameTargetIndicesByElementNames[elementName].add(frame.tokenIndex)

    framesByElementNames = {}

    for elementName in frameElementNames:

        if elementName not in frameTargetIndicesByElementNames:
            frameTargetIndicesByElementNames[elementName] = set()

        elementsWithFrames = Dict(elementName=elementName, tokenIndices=set(), frames=[])

        function = frameElementFunctions[elementName]

        for token in tokens:
            r = function(**frameElementFeatures(token=token, tokens=tokens, elementName=elementName,
                indicesOfTargetTokens=frameTargetIndicesByElementNames[elementName]))
            if r == 'YES':
                # pievieno atrastā elementa tokena indeksu
                elementsWithFrames.tokenIndices.add(token.index)

        # pievieno elementam atbilstošos freimus
        if elementsWithFrames.tokenIndices:
            for frame in frames:
                if elementName in frameTypesWithElementNames[frame.type]:
                    elementsWithFrames.frames.append(frame)

        # ir vērts pievienot tikai tad, ja ir atrasts vismaz kāds elements un tam atbilstoši freimi
        if elementsWithFrames.tokenIndices and elementsWithFrames.frames:
            framesByElementNames[elementName] = elementsWithFrames

    return framesByElementNames
"""
