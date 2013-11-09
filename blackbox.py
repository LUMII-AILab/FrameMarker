#!/usr/bin/env python3

import os, sys, json, subprocess, re
import loader
from utils import Dict
from data import Data, Category
from rulesdb import RulesDB, saveCombined


# šis modulis atbild par datu sagatavošanu, likumu ģenerēšanu ar C5.0
# framenets (framenet.json) ir nošķirts no likumiem


class EmptyRuleGenerator:

    def __init__(self):
        pass

    def __call__(self, data, **config):
        # TODO: kādā formātā būs outputs ?
        pass


class C5:

    def __init__(self, filesystem='tmp', command=['./bin/osx/c5.0'], args=['-r', '-m1', '-c100'], costs=100, skipC5=False):
        self.filesystem = filesystem
        self.command = command + args
        self.costs = costs
        self.skipC5 = skipC5
        # for internal use
        self.escapeSymbol = '\\'
        self.toEscape = ['\\', ',', ':', '.', '|']

    def escape(self, s):
        if type(s) != str:
            return str(s)
        for c in self.toEscape:
            s = s.replace(c, self.escapeSymbol+c)
        return s

    def __call__(self, data, category, **config):

        filesystem = self.filesystem
        config = Dict(config)
        if config.filesystem:
            filesystem = os.path.join(filesystem, config.filesystem)
        if type(category) == str:
            filesystem = os.path.join(filesystem, category)
        else:
            filesystem = os.path.join(filesystem, category.name)

        dirname = os.path.dirname(filesystem)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)


        # if not config.skipC5:
        if not self.skipC5:

            features = data.features

            #
            # prepare
            #

            # write .names
            with open(filesystem+'.names', 'w') as f:
                # NOTE: YES, NO - otrādi nedarbojas
                # print(', '.join(reversed(self.classes)),'.', sep='', file=f)
                print('YES, NO.', file=f)
                print('', file=f)

                for feature in features:
                    if feature.type == int:
                        description = 'continuous'
                    else:
                        description = 'discrete 1000000'
                    print(self.escape(feature.name), ': ', description, '.', sep='', file=f)

            # write .costs
            with open(filesystem+'.costs', 'w') as f:
                # NOTE: NO, YES - otrādi nedarbojas
                # print(', '.join(self.classes),': '+str(self.costs), sep='', file=f)
                print('NO, YES:', self.costs, file=f)


            #
            # write data
            #

            # open new .data
            YN = {}
            YN[False] = 'NO'
            YN[True] = 'YES'
            with open(filesystem+'.data', 'w') as f:
                for row,value in zip(data, category):
                    if value is None:
                        continue
                    print(','.join(self.escape(component) for component in row), ',', YN[value], '.', sep='', file=f)
                

            #
            # run c5.0
            #

            f = open(filesystem+'.out', 'w')
            # izpilda C5 klasifikātoru    
            rc = subprocess.call(self.command + ['-f', filesystem], stdout=f)
            f.close()
            if rc != 0:
                print('Error: C5.0 exit with code:', rc, file=sys.stderr)
                # TODO: output formāts ?
                return False

        

        #
        # parse rules
        #

        def parse(line):
            params = Dict()
            keys = []
            for param in re.findall(r'([a-z]+=(?:(?:""|".*?[^\\]")(?:,\s?)?)+)', line):
                key, values = param.split('=', 1)
                values = list(value.strip('"') for value in re.findall(r'(""|".*?[^\\]")(?:,\s?)?', values))
                keys.append(key)
                if len(values) == 0:
                    params[key] = ''
                elif len(values) == 1:
                    params[key] = values[0]
                else:
                    params[key] = values
            return keys, params


        # extracted feature values
        values = dict()
        expectedRuleCount = 0
        defaultClassName = ''
        rules = []

        with open(filesystem+'.rules') as f:

            rule = None
            operations = ['0?', '==', '2?', 'in', '4?', '5?', '6?', '7?', '8?']
            classToValue = {}
            classToValue['YES'] = True
            classToValue['NO'] = False

            for line in f:
                line = line.rstrip()
                keys, params = parse(line)

                if not keys:
                    continue

                if keys[0] == 'att':
                    values[params.att] = params.elts
                    continue

                if keys[0] == 'rules':
                    expectedRuleCount = int(params.rules)
                    defaultClassName = params.default

                if keys[0] == 'conds':
                    if rule and rule.value: # šobrīd nevajag negatīvos likumus
                        rules.append(rule)
                    # rule = Dict(conditionCount=params.conds, conditions=[],
                    #         className=params['class'], cover=params.cover, ok=params.ok, lift=params.lift)
                    # name=category.name vajag? nevajag?
                    rule = Dict(conditions=[], value=classToValue[params['class']],
                            cover=int(params.cover), ok=int(params.ok), lift=float(params.lift))
                elif rule:
                    if int(params.type) == 2:
                        operation = params.result
                        if operation == '<':
                            operation = '<='
                    else:
                        operation = operations[int(params.type)]
                    if operation.endswith('?'):
                        print('Warning: unknown operation type:', operation)
                        # print('Warning: unknown operation type:', params.type)
                    condition = Dict(name=params.att, op=operation)
                    if int(params.type) == 3:
                        # in ?
                        condition.value = params.elts
                    elif int(params.type) == 2:
                        condition.value = int(params.cut)
                    else:
                        condition.value = params.val
                    rule.conditions.append(condition)
                    # rule.conditions.append(Dict(name=params.att, operation=operation, value=params.val))    # feature name and feature value

                # debug
                # print('  '.join(key+'='+params[key] for key in keys), file=sys.stderr)

            if rule and rule.value: # šobrīd nevajag negatīvos likumus
                rules.append(rule)

            if expectedRuleCount < len(rules):
                print('Warning: not all expected rules extracted', file=sys.stderr)

        # self.defaultClassName = defaultClassName
        # self.rules = rules
        # self.values = values

        # force default class name to NO
        # self.defaultClassName = "NO"

        return rules



class BlackBox:

    def __init__(self, trainPaths, features='features', filesystem='default'):

        self.filesystem = filesystem
        self.trainPaths = trainPaths

        if not os.path.isdir(filesystem):
            os.makedirs(filesystem)

        def importfrom(modulename, *fromlist):
            module = __import__(modulename, globals(), locals(), fromlist, 0)
            return tuple(getattr(module, name) for name in fromlist)
        
        # dinamiska features moduļa ielāde
        self.frameTargetFeatures, self.frameElementFeatures = importfrom(features, 'frameTargetFeatures', 'frameElementFeatures')

        self.documents = []
        self.frameNET = {}

        frameNETfilename = "framenet.json"
        if os.path.isfile(frameNETfilename):
            # ielādēt no json
            with open(frameNETfilename) as f:
                self.frameNET = json.load(f, object_hook=Dict)
        else:
            self.frameNET = loader.loadPredefinedFrameNET()
            self.loadTrainData()
            with open(frameNETfilename, 'w') as f:
                json.dump(self.frameNET, f, indent=4, sort_keys=True)

        # izvelkt visus elementus
        self.frameElementNames = set()
        self.frameTypes = set()
        for frameType, elementNames in self.frameNET.items():
            self.frameTypes.add(frameType)
            for elementName in elementNames:
                self.frameElementNames.add(elementName)


    def loadTrainData(self, trainPaths=None):
        if trainPaths is None:
            trainPaths = self.trainPaths

        print('Loading train data:')
        for document in loader.loadDocumentsFromPaths2(trainPaths, sys.stderr, True):
            loader.updateFrameNET(document.sentences, self.frameNET)
            self.documents.append(document)


    def load(self, dataClass=Data, categoryClass=Category, noData=False):

        print('Loading frame data ... ', end='')
        sys.stdout.flush()

        self.frameData = dataClass(self.frameTargetFeatures, os.path.join(self.filesystem, 'targets'))
        self.frameData.load(noData)

        print('ok')
        sys.stdout.flush()

        print('Loading frame element data ... ', end='')
        sys.stdout.flush()

        self.frameElementData = dataClass(self.frameElementFeatures, os.path.join(self.filesystem, 'elements'))
        self.frameElementData.load(noData)

        print('ok')
        sys.stdout.flush()


    def generateData(self, dataClass=Data, categoryClass=Category):

        # ielādē treniņdatus
        if not self.documents:
            self.loadTrainData()

        # treniņdati ir ielādēti

        # frame target feature data
        data = dataClass(self.frameTargetFeatures, os.path.join(self.filesystem, 'targets'))

        data.reset()

        # create categories
        for frameType in self.frameTypes:
            category = categoryClass(data, frameType)
            # TODO: bez šī soļa vajadzētu iztikt (automātiska salinkošana, pagaidām nav)
            data.categories[frameType] = category

        data.reset()

        print('Generating frame data ', end='')
        sys.stdout.flush()

        for document in self.documents:
            for sentence in document.sentences:
                # if not sentence.frames:
                #     sentence.frames = []
                
                for token in sentence.tokens:
                    data.add(token=token, tokens=sentence.tokens)

                for frameType, category in data.categories.items():

                    targetTokenIndices = set()

                    for frame in sentence.frames:
                        # if frame.tokenIndex <= 0:
                        #     continue
                        if frame.type == frameType:
                            targetTokenIndices.add(frame.tokenIndex)

                    for token in sentence.tokens:
                        category.add(token.index in targetTokenIndices)

                print('.', end='')
                sys.stdout.flush()

        data.save()

        self.frameData = data

        print(' ok')
        sys.stdout.flush()



        # tālāk freimu elementu pazīmju dati

        data = dataClass(self.frameElementFeatures, os.path.join(self.filesystem, 'elements'))

        # create categories
        for frameElementName in self.frameElementNames:
            category = categoryClass(data, frameElementName)
            # TODO: bez šī soļa vajadzētu iztikt (automātiska salinkošana, pagaidām nav)
            data.categories[frameElementName] = category

        data.reset()

        print('Generating frame element data ', end='')
        sys.stdout.flush()

        for document in self.documents:
            for sentence in document.sentences:
                # if not sentence.frames:
                #     sentence.frames = []

                # category vajag trīs vērtības: True/False/None

                for frame in sentence.frames:
                    # if frame.tokenIndex <= 0:
                    #     continue

                    for element in frame.elements:
                        if element.tokenIndex is None or element.tokenIndex <= 0:
                            continue

                        # katram freimam pievieno visu teikumu datos
                        for token in sentence.tokens:
                            data.add(token=token, tokens=sentence.tokens, frame=frame)

                        for elementName, category in data.categories.items():

                            for token in sentence.tokens:
                                if element.name == elementName:
                                    category.add(token.index == element.tokenIndex)
                                else:
                                    # te ir divi varianti: False vai None
                                    # category.add(None)  # mazāk datu
                                    category.add(False)

                print('.', end='')
                sys.stdout.flush()


        data.save()

        self.frameElementData = data

        print(' ok')
        sys.stdout.flush()


    def extractRules(self, generator=EmptyRuleGenerator(), rulesDBClass=RulesDB):

        # ieraksta datu failu, pārējos failus, izsauc c5.0, izveido likumus, saglabā likumus JSON formātā

        print('Extracting frame target rules ', end='')
        sys.stdout.flush()

        targetRulesDB = rulesDBClass(self.frameData.features, 'targets', filesystem=os.path.join(self.filesystem, 'rules'))
        # just in case
        targetRulesDB.name = 'targets'

        for category in sorted(self.frameData.categories.values(), key=lambda cat: cat.name):
            rules = generator(self.frameData, category, filesystem='targets')
            targetRulesDB[category.name] = rules
            print('.', end='')
            sys.stdout.flush()

        targetRulesDB.save()

        print(' ok')
        sys.stdout.flush()


        print('Extracting frame element rules ', end='')
        sys.stdout.flush()

        elementRulesDB = rulesDBClass(self.frameElementData.features, 'elements', filesystem=os.path.join(self.filesystem, 'rules'))
        # just in case
        elementRulesDB.name = 'elements'

        for category in sorted(self.frameElementData.categories.values(), key=lambda cat: cat.name):
            rules = generator(self.frameElementData, category, filesystem='elements')
            elementRulesDB[category.name] = rules
            print('.', end='')
            sys.stdout.flush()
            # debug outputs
            # for rule in rules:
            #     if rule.ok > 0 and rule.ok != rule.cover:
            #         print(category.name, 'Expected:', rule.ok, rule.cover, 'Got:', category.cover(rule))
            #         print(rule)

        elementRulesDB.save()

        print(' ok')
        sys.stdout.flush()


        return targetRulesDB, elementRulesDB





from data import SQLiteData, SQLiteCategory


trainPaths = "./train_reparsed"
# trainPaths = "./train_reparsed/parsera_sintakse/Ziedonis"

blackbox = BlackBox(trainPaths, 'features5', filesystem='default')

# Trīs variant:
# 1. ģenerēt datus no treniņdatiem
# blackbox.generateData(SQLiteData, SQLiteCategory)
# 2. izmantot jau ģenerētus datus, bet pārģenerēt likumus ar C5
# blackbox.load(SQLiteData, SQLiteCategory)
# 3. neģenerēt datus, nepārģenerēt likumus ar C5, tikai izvilkt likumus no iepriekš ģenerētajiem C5 .rules failiem
blackbox.load(SQLiteData, SQLiteCategory, noData=True)

# ģenerēt likumus ar C5 (neizmantot kopā ar 3. iepriekšējā solī)
# c5 = C5(filesystem=os.path.join(blackbox.filesystem, 'c5'))
# tikai likumu izvilkšana no jau iepriekš ģenerētiem C5 .rules failiem (izmantot kopā ar 3. iepriekšējā solī)
c5 = C5(filesystem=os.path.join(blackbox.filesystem, 'c5'), skipC5=True)

# izsauc likumu ģenerēšanu+izvilkšanu/tikai izvilkšanu
targetRulesDB, elementRulesDB = blackbox.extractRules(c5)

# saglabā kombinēto (all.json) likumu failu
saveCombined(targetRulesDB, elementRulesDB, filesystem=os.path.join(blackbox.filesystem, 'rules'))



