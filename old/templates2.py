#!/usr/bin/env python3


header = """#!/usr/bin/env python
# coding=utf-8
# for Python 2 compatibility
# convert to unicode strings with vim : %%s/"\([^"]*\)"/u"\\1"/g

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
            ok = function(**frameTargetFeatures(token=token, tokens=tokens))
            if ok:
                frames.append(Dict(type=frameType, tokenIndex=token.index, elements=[]))

    return frames



def getFrameElements(tokens, frames, maxdist=3):

    frameTargetIndicesByElementNames = {}

    # sagrupē freimu targetus pēc elementu nosaukumiem
    for frame in frames:
        for elementName in frameTypesWithElementNames[frame.type]:

            function = frameElementFunctions[elementName]

            for token in tokens:
                ok = function(**frameElementFeatures(token=token, tokens=tokens, elementName=elementName, frame=frame))
                if ok:
                    try:
                        if 'distances' not in tokens[frame.tokenIndex] or token.index == frame.tokenIndex or len(tokens[frame.tokenIndex].distances[token.index]) <= maxdist:
                            frame.elements.append(Dict(tokenIndex=token.index, name=elementName))
                    except:
                        # var gadītites, ka ir problēmas ar distances masīvu, tad ignorē un pievieno tik un tā
                        frame.elements.append(Dict(tokenIndex=token.index, name=elementName))

"""
