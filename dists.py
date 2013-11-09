#!/usr/bin/env python3

import json
from loader import pathIterator2
from utils import Dict

frameStats = {}

# trainPaths = ['./train_reparsed/*/*.json', './train_reparsed/parsera_sintakse/*/*.json']
trainPaths = ['../SemanticAnalyzer/SemanticData/Corpora/json']

distances = {}

import loader, sys

for document in loader.loadDocumentsFromPaths2(trainPaths, sys.stderr, True):
    for sentence in document.sentences:
        if not sentence.frames:
            continue
        for frame in sentence.frames:
            for element in frame.elements:
                if element.tokenIndex is None:
                    continue
                dist = len(sentence.tokens[element.tokenIndex].distances[frame.tokenIndex])
                if dist not in distances:
                    distances[dist] = 0
                distances[dist] += 1

for dist in distances:
    print('Distance', dist, '=>', distances[dist], 'occurrences')
