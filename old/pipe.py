#!/usr/bin/env python3

import os, sys, json
from utils import Dict
import loader



# gmode = len(sys.argv) > 1 and sys.argv[1].startswith('g') and sys.argv[1] or ''
gmode = len(sys.argv) > 1 and sys.argv[1] or ''



# old
# if gmode:
#     from rulesg import getFrames, getFrameElements
# else:
#     from rules import getFrames, getFrameElements

# new
def importfrom(modulename, *fromlist):
    module = __import__(modulename, globals(), locals(), fromlist, 0)
    return tuple(getattr(module, name) for name in fromlist)

# dinamiska features moduļa ielāde
getFrames, getFrameElements = importfrom('rules'+gmode, 'getFrames', 'getFrameElements')

# getFrames(tokens)
# getFrameElements(tokens, frames)
 


input_path = 'input/*'
output_dir = 'output'

if not os.path.isdir(output_dir):
    os.mkdir(output_dir)



def strength(rule):
    # r = (rule.ok+1)/(rule.cover+10)
    r = (float(rule.ok)+1.0)/(float(rule.cover)+2.0)
    return '%.03f' % (r,)
    # return r


def markFrames(filename):

    print()
    print()
    print('###', filename, '###')
    print()

    document = loader.loadDocument(filename, True)

    for sentence in document.sentences:
        print(sentence.text)
        # loader.outputSentence(sentence)
        frames = getFrames(sentence.tokens)
        # for frame in frames:
        #     print('>>> Frame:', frame.type, '=', frame.tokenIndex)

        # maxdist=n - ierobežo attālumu pa koku
        getFrameElements(sentence.tokens, frames, maxdist=3)


        for frame in frames:
            # print('>>> Frame:', frame.type, '=', frame.tokenIndex, '[%s]' % (','.join(str(strength(rule)) for rule in frame.rules),))
            if frame.rules:
                rulestrength = '[%s]' % (','.join(str(strength(rule)) for rule in frame.rules),)
            else:
                rulestrength = ''
            print('>>> Frame:', rulestrength, frame.type, '=', frame.tokenIndex)
            # print('>>>>>>>>>>>>>>>>>>>>', len(frame.rules))
            for element in frame.elements:
                # print('>>>>>>>>>>>>>>>>>>>>', len(element.rules))
                # print('>>>>>> Element:', element.name, '=', element.tokenIndex, '[%s]' % (','.join(strength(rule) for rule in element.rules),))
                if element.rules:
                    rulestrength = '[%s]' % (','.join(strength(rule) for rule in element.rules),)
                else:
                    rulestrength = ''
                print('>>>>>> Element:', rulestrength, element.name, '=', element.tokenIndex)



        # frameElements = getFrameElements(sentence.tokens, frames)
        # for frameElementName, frameElement in frameElements.items():
        #     print('>>> Frame Element:', frameElementName, '(%s)' % (','.join(str(idx) for idx in frameElement.tokenIndices)),
        #             'for frames:', ' | '.join('%s (%i)' % (frame.type, frame.tokenIndex) for frame in frameElement.frames))
        #     # print(frameElement.tokenIndices)
        #     # print(frameElement.frames)
        #     # for frame in frameElement.frames:
        #     #     print(frame)

        sentence.frames = frames

        print()
        print()

    # saglabā outputu
    loader.cleanSentences(document.sentences)
    json.dump(document, open(os.path.join(output_dir, os.path.basename(filename)), 'w'), indent=4)




for path in loader.pathIterator(input_path):
    # pašlaik tikai .json, jo nav pārējie rīki, kas sagatavotu nepieciešamo info
    if path.endswith('.json'):
        markFrames(path)


# markFrames('train_auto/Diena_01.json')
# markFrames('input/teksts.json')
# markFrames('input/tvnet.json')



