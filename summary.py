#!/usr/bin/env python3

import json
from loader import pathIterator2
from utils import Dict

paths = '../SemanticAnalyzer/SemanticData/Corpora/json'

# import glob
# for p in glob.glob(paths):
#     print(p)
# quit()

frameStats = {}

for path in pathIterator2(paths):
    if not path.endswith('.json'):
        continue

    print(path)

    with open(path) as f:
        document = json.load(f, object_hook=Dict)

    for sentence in document.sentences:
        if not sentence.frames:
            continue

        for frame in sentence.frames:

            if frame.type not in frameStats:
                frameStats[frame.type] = Dict(count=0, elementNames={}, targets={})

            stats = frameStats[frame.type]
            stats.count += 1

            target = sentence.tokens[frame.tokenIndex-1].lemma
            if target not in stats.targets:
                stats.targets[target] = 1
            else:
                stats.targets[target] += 1

            for element in frame.elements:

                if element.name not in stats.elementNames:
                    stats.elementNames[element.name] = 0

                stats.elementNames[element.name] += 1


with open('summary.txt', 'w') as f:

    for frameType,stats in frameStats.items():
        print('>>', frameType, file=f)

        for target,count in stats.targets.items():

            print('    ', target, '=', count, file=f)

    # for frameType,stats in frameStats.items():
    #     print('>>', frameType, '=', stats.count, file=f)

    #     for elementName,count in stats.elementNames.items():

    #         print('    ', elementName, '=', count, file=f)


