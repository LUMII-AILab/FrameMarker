#!/usr/bin/env python3

import subprocess, os, sys, re
from utils import Dict

# NOTE: tagad tas notiek dinamiski, sk. blackBox()
# from features import frameTargetFeatures, frameElementFeatures


class C5:

    def __init__(self, filesystem, features, classes=['NO', 'YES'], command=['./c5.0', '-r', '-m1', '-c100'], costs=200):
        self.filesystem = filesystem.replace('ā', 'a')
        # self.filesystem = filesystem
        self.features = features
        self.classes = classes
        self.command = command
        self.costs = costs

        self.escapeSymbol = '\\'
        self.toEscape = ['\\', ',', ':', '.', '|']

        self.datafile = None
        self.devnull = None

    def escape(self, s):
        for c in self.toEscape:
            s = s.replace(c, self.escapeSymbol+c)
        return s

    def prepare(self):

        # write .names
        with open(self.filesystem+'.names', 'w') as f:
            # NOTE: YES, NO - otrādi nedarbojas
            print(', '.join(reversed(self.classes)),'.', sep='', file=f)
            print('', file=f)
            for feature in self.features:
                print(self.escape(feature.name), ': ', feature.description, '.', sep='', file=f)

        # write .costs
        with open(self.filesystem+'.costs', 'w') as f:
            # NOTE: NO, YES - otrādi nedarbojas
            # print(', '.join(reversed(self.classes)),': 200', sep='', file=f)
            print(', '.join(self.classes),': '+str(self.costs), sep='', file=f)

        # open new .data
        self.datafile = open(self.filesystem+'.data', 'w')

    def close(self):
        if self.datafile:
            self.datafile.close()
            self.datafile = None

    def __call__(self, *args, **kargs):

        if '_class' not in kargs:
            return False

        _class = kargs['_class']

        output = self.features(*args, **kargs)

        # NOTE: šeit ir jāpārbauda, vai kāds no output elementiem nav masīvs (jābūt ir stringam), ja ir masīvs,
        # tad izvada vienu ierakstu katram elementam, turklā tie paralēlie elementi, kas nav masīvi tiek kopēti,
        # ja eksistē vairāk kā viens masīva elements, tad šo masīvu garumiem ir jāsakrīt un pie izvadīšanas 
        # tiek zip veidā savienoti kopā: pirmais ar pirmo, otrais ar otro utt.

        # ja kāds no elementiem ir [] vai '', tad to varētu automātiski aizvietot ar NONE placeholderi

        # NOTE: ŠIS KODS NAV PĀRBAUDĪTS !

        count = 0
        for key,value in output.items():
            if value is None or value == '':
                # vai tas ir atļauts iterāciju laikā ?
                output[key] = self.features.NONE
                continue
            if type(value) == list or type(value) == tuple:
                if count == 0:
                    count = len(value)
                elif count != len(value):
                    print('ERROR: feature output length (name=%s) length mismatch, expected %i, got %i' % (key,count,len(value)))
                    return False
            if type(value) == int or type(value) == float:
                output[key] = str(value)

        if count == 0:
            print(','.join(self.escape(output[feature.name]) for feature in self.features), ',', _class, '.', sep='', file=self.datafile)
        elif count > 0:

            def ith(feature, i):
                if type(value) == list or type(value) == tuple:
                    return output[feature.name][i]
                return output[feature.name]

            for i in range(count):
                print(','.join(self.escape(ith(feature, i)) for feature in self.features), ',', _class, '.', sep='', file=self.datafile)


        return True

    def run(self):
        # aizver datu failu
        self.close()

        # atver /dev/null, kur ierakstīt outputu
        # if not self.devnull:
        #     self.devnull = open(os.devnull, 'w')

        f = open(self.filesystem+'.out', 'w')

        # izpilda C5 klasifikātoru    
        # rc = subprocess.call(self.command + ['-f', self.filesystem], stdout=self.devnull)
        rc = subprocess.call(self.command + ['-f', self.filesystem], stdout=f)

        f.close()

        # aizver /dev/null
        # self.devnull.close()

        if rc != 0:
            print('Error: C5.0 exit with code:', rc, file=sys.stderr)
            return False

        return True

    def loadRules(self):

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

        with open(self.filesystem+'.rules') as f:

            rule = None
            operations = ['0?', '==', '2?', 'in', '4?', '5?', '6?', '7?', '8?']

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
                    if rule:
                        rules.append(rule)
                    rule = Dict(conditionCount=params.conds, conditions=[],
                            className=params['class'], cover=params.cover, ok=params.ok, lift=params.lift)
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
                    condition = Dict(name=params.att, operation=operation)
                    if int(params.type) == 3:
                        condition.value = params.elts
                    elif int(params.type) == 2:
                        condition.value = int(params.cut)
                    else:
                        condition.value = params.val
                    rule.conditions.append(condition)
                    # rule.conditions.append(Dict(name=params.att, operation=operation, value=params.val))    # feature name and feature value

                # debug
                # print('  '.join(key+'='+params[key] for key in keys), file=sys.stderr)

            if expectedRuleCount < len(rules):
                print('Warning: not all expected rules extracted', file=sys.stderr)

        self.defaultClassName = defaultClassName
        self.rules = rules
        self.values = values

        # force default class name to NO
        self.defaultClassName = "NO"


    def printRules(self):
        for rule in self.rules:
            print('Rule:', rule.className)
            for condition in rule.conditions:
                print('  ', condition.name, condition.operation, condition.value)
        print('Default:', self.defaultClassName)


    # ģenerē python if-rules
    def generate(self, indent=4, file=sys.stdout, skipNOrules=True):

        def quote(s):

            if type(s) == int or type(s) == float:
                return str(s)
            # print(type(s))
            if type(s) == str:
                s = s.replace('"', '\\"').replace('\\', '\\\\')
                return '"'+s+'"'
            return '('+','.join(quote(x) for x in s)+')'
            # if type(s) == list or type(s) == tuple:
            #     return '('+','.join(quote(x) for x in s)+')'
            # return str(s)

        def prep(s):
            if type(s) == str:
                return s
            if type(s) == int or type(s) == float:
                return str(s)
            return '('+','.join(x for x in s)+')'

        # Original C5.0 output sample:
        # Rule 146: (15, lift 1.0)
        #     lemma = savukārt
        #         ->  class NO  [0.941]

        indent = ' ' * indent

        print(file=file)
        # print(indent+'rules = []', file=file)
        # print(file=file)

        for rule in self.rules:

            if rule.className != "YES":
                continue

            # if float(rule.ok) / float(rule.cover) < 0.4:
            #     continue

            # print comment
            # print(indent+'# Rule:', rule.ok, 'of', rule.cover, 'OK', file=file)
            # for condition in rule.conditions:
            #     print(indent+'#    ', condition.name, condition.operation, quote(condition.value), file=file)
            # print(indent+'#     ->', rule.className, '[%.3f]' % (float(rule.lift) / 100), file=file)
            print(indent+'# Coverage:', rule.ok, 'of', rule.cover, 'ok', '[%.3f]' % (float(rule.lift) / 100), file=file)
            for condition in rule.conditions:
                condop = condition.operation
                if condop == '==':
                    condop = '='
                print(indent+'#    ', condition.name, condop, prep(condition.value), file=file)
                # print(indent+'#    ', condition.name, condition.operation, prep(condition.value), file=file)
                # print(indent+'#    ', condition.name, condition.operation, quote(condition.value), file=file)
            # print(indent+'#     ->', rule.className, '[%.3f]' % (float(rule.lift) / 100), file=file)

            # print python if-rule code
            # print(condition)
            # print(condition.operation)
            condstr = ' and '.join('%s %s %s' % (condition.name, condition.operation, quote(condition.value)) for condition in rule.conditions)
            print(indent+'if', condstr+':', end='', file=file)
            print(' return True', file=file)
            # print(' return [%i,%i]' % (int(rule.ok), int(rule.cover)), file=file)

            # print(indent+'    if not forClassName or forClassName == "%s":' % (rule.className,), file=file)
            # print(indent+'        rules.append(Dict(className="%s", cover=%s, ok=%s, text="""%s -> %s"""))'
                    # % (rule.className, rule.cover, rule.ok, condstr, rule.className), file=file)
            print(file=file)

            # old & simple:
            # condstr = ' and '.join('%s %s %s' % (condition.name, condition.operation, quote(condition.value)) for condition in rule.conditions)
            # print(indent+'if', condstr+':', file=file)
            # print(indent+'    return ("%s", %s, %s, """%s -> %s""")' % (rule.className, rule.cover, rule.ok, condstr, rule.className), file=file)
            # print(file=file)

        # old & simple
        # print(indent+'return ("%s", 0, 0, "default")'% (self.defaultClassName,), file=file)

        # print(indent+'# default rule:', self.defaultClassName, file=file)
        # print(indent+'if not forClassName or forClassName == "%s":'% (self.defaultClassName,), file=file)
        # print(indent+'    rules.append(Dict(className="%s", cover=0, ok=0, text="default"))'% (self.defaultClassName,), file=file)
        # print(file=file)
        # print(indent+'return rules', file=file)
        print(indent+'return False', file=file)
        print(file=file)

        # TESTAM, lai redzētu, vai strength kritērijs ir dilstošs
        # def strength(rule):
        #     r = (float(rule.ok)+1.0)/(float(rule.cover)+2.0)
        #     return '%.03f' % (r,)
        # print()
        # print('['+','.join(strength(rule) for rule in self.rules if rule.className == "YES")+']')
        # print()

        return True



#
# Tipiskais C5 workflow piemērs:
#
# for frameType in frameTypes:
#     c5 = C5(filesystem=..., features=..., tmpdir=..., classes=..., command=...)
# 
#     if generate:
#         c5.prepare()
#         for token in tokens:
#             c5(token, tokens, ..., _class=...)
#         c5.run()
# 
#     c5.loadRules()
#     c5.generate(file=...)
#
# Šis koks iekļaujas rules.py ierakstīšanas kodā
#



def blackBox(trainPaths='train/*', features='features', filename='./rules.py', tmpdir='tmp', runC5Targets=True, runC5Elements=True,
        allSentences=False, command=['./c5.0'], args=['-r', '-m1', '-c100'], mode='new', costs=200):

    if type(command) == str:
        command = [command]

    # prepare directories
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    if not os.path.isdir(tmpdir+'/targets'):
        os.mkdir(tmpdir+'/targets')
    if not os.path.isdir(tmpdir+'/elements'):
        os.mkdir(tmpdir+'/elements')

    
    import loader


    frameTypesWithElementNames = {}
    documents = []

    print('Loading train data:')
    for document in loader.loadDocumentsFromPaths(trainPaths, sys.stderr, True):
        frameTypesWithElementNames = loader.getFrameTypesWithElementNames(document.sentences, frameTypesWithElementNames)
        documents.append(document)

    frameElementNames = set()
    for frameType, elementNames in frameTypesWithElementNames.items():
        frameElementNames |= elementNames

    # open rules file for writing
    f = open(filename, 'w')

    import templates2 as templates
    # import templates3 as templates


    print(templates.header % features, file=f)

    
    def importfrom(modulename, *fromlist):
        module = __import__(modulename, globals(), locals(), fromlist, 0)
        return tuple(getattr(module, name) for name in fromlist)


    # dinamiska features moduļa ielāde
    frameTargetFeatures, frameElementFeatures = importfrom(features, 'frameTargetFeatures', 'frameElementFeatures')


    print('frameTypesWithElementNames = {', file=f)
    for frameType in sorted(frameTypesWithElementNames):
        print('    "'+frameType+'": {', file=f)
        for frameElementName in sorted(frameTypesWithElementNames[frameType]):
            print('        "'+frameElementName+'",', file=f)
        print('    },', file=f)
    print('}', file=f)
    print(file=f)

    print(templates.allElements, file=f)

    # runC5 = True
    # runC5 = False


    print()
    if runC5Targets:
        print('Training frames and extracting frame rules:')
    else:
        print('Extracting frame rules only:')

    for frameType in sorted(frameTypesWithElementNames.keys()):

        # print('Frame Targets of type:', frameType, '... ', end='', flush=True)   # requires Python 3.3
        print('Frame Targets of type:', frameType, '... ', end='')
        sys.stdout.flush()

        c5 = C5(filesystem=tmpdir+'/targets/'+frameType, features=frameTargetFeatures, command=command+args, costs=costs)

        if runC5Targets:
            c5.prepare()

            # print('generate data ... ', end="", flush=True)   # requires Python 3.3
            print('generate data ... ', end="")
            sys.stdout.flush()
            
            for document in documents:
                for sentence in document.sentences:
                    # if not sentence.frames:
                    #     sentence.frames = []

                    targetTokenIndices = set()

                    for frame in sentence.frames:
                        if frame.type == frameType:
                            targetTokenIndices.add(frame.tokenIndex)

                    
                    # NOTE: ja grib pazīmes/atribūtus ar vairākām vērtībām (piemēram, child tokenu lemmas utt.), tad:
                    # * c5 ir jāizsauc vairākkārt ar katru vērtību
                    # * pazīmi ģenerējošām funkcijām ir jāatgriež masīvs (ja vairākas pazīmes atgriež masīvus, tad to garumam ir jāsakrīt)
                    # * jāpievieno klāt pazīmes, kur katra pazīme savai vērtībai, bet šis ir neoptimāls variants (ir jāveic sortēšana, lai
                    #   kārtība nemainītos
                    # TODO: ir jāapdomā, vai tādā gadījumā nav jāpievieno arī kāds pretsvars
                    for token in sentence.tokens:
                        c5(token=token, tokens=sentence.tokens, _class=c5.classes[token.index in targetTokenIndices])

            # print('runing c5 ... ', end='', flush=True)   # requires Python 3.3
            print('runing c5 ... ', end='')
            sys.stdout.flush()
            c5.run()

        # print('loading rules ... ', end='', flush=True)   # requires Python 3.3
        print('loading rules ... ', end='')
        sys.stdout.flush()
        c5.loadRules()

        # print('generating rules ... ', end='', flush=True)   # requires Python 3.3
        print('generating rules ... ', end='')
        sys.stdout.flush()

        # print('def FrameType_', frameType, '(', ', '.join(feature.name for feature in frameTargetFeatures), ', forClassName="YES"):', sep='', file=f)
        print('def FrameType_', frameType, '(', ', '.join(feature.name for feature in frameTargetFeatures), '):', sep='', file=f)
        c5.generate(indent=4, file=f)
        print(file=f)

        # print('ok', flush=True)   # requires Python 3.3
        print('ok')
        sys.stdout.flush()







    # runC5 = True
    # runC5 = False


    print()
    if runC5Elements:
        print('Training frame elements and extracting frame element rules:')
    else:
        print('Extracting frame element rules only:')



    for frameElementName in sorted(frameElementNames):

        print('Frame Element name:', frameElementName, '... ', end='')
        sys.stdout.flush()

        c5 = C5(filesystem=tmpdir+'/elements/'+frameElementName, features=frameElementFeatures, command=command+args, costs=costs)

        if runC5Elements:
            c5.prepare()

            print('generate data ... ', end="")
            sys.stdout.flush()

            for document in documents:
                for sentence in document.sentences:
                    # if not sentence.frames:
                    #     sentence.frames = []


                    # NOTE: ja grib pazīmes/atribūtus ar vairākām vērtībām (piemēram, child tokenu lemmas utt.), tad:
                    # * c5 ir jāizsauc vairākkārt ar katru vērtību
                    # * pazīmi ģenerējošām funkcijām ir jāatgriež masīvs (ja vairākas pazīmes atgriež masīvus, tad to garumam ir jāsakrīt)
                    # * jāpievieno klāt pazīmes, kur katra pazīme savai vērtībai, bet šis ir neoptimāls variants (ir jāveic sortēšana, lai
                    #   kārtība nemainītos
                    # TODO: ir jāapdomā, vai tādā gadījumā nav jāpievieno arī kāds pretsvars


                    # vecais variants

                    elementTokenIndices = set()
                    targetTokenIndices = set()

                    # viens un tas pats elements var būt vairāku freimu targetiem

                    # for frame in sentence.frames:
                    #     for element in frame.elements:
                    #         if element.name == frameElementName:
                    #             elementTokenIndices.add(element.tokenIndex)

                    #             # šāds elements vispār pieder pie attiecīgā freima tipa
                    #             # if element.name in frameTypesWithElementNames[frame.type]:
                    #             targetTokenIndices.add(frame.tokenIndex)

                    # if allSentences or targetTokenIndices:
                    #     for token in sentence.tokens:
                    #         # šo var izsaukt vairākreiz katram target token indexam, vai tā nebūs pareizāk ?
                    #         c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                    #             indicesOfTargetTokens=targetTokenIndices, _class=c5.classes[token.index in elementTokenIndices])


                    if mode == 'simple':
                        for frame in sentence.frames:
                            for element in frame.elements:
                                if element.name == frameElementName:
                                    elementTokenIndices.add(element.tokenIndex)

                                    # šāds elements vispār pieder pie attiecīgā freima tipa
                                    # if element.name in frameTypesWithElementNames[frame.type]:
                                    targetTokenIndices.add(frame.tokenIndex)

                        if allSentences or targetTokenIndices:
                            for token in sentence.tokens:
                                # šo var izsaukt vairākreiz katram target token indexam, vai tā nebūs pareizāk ?
                                c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                                    frame=None, _class=c5.classes[token.index in elementTokenIndices])

                    if mode == 'perframetarget':
                        for frame in sentence.frames:
                            for element in frame.elements:
                                for token in sentence.tokens:
                                    c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                                        frame=frame, _class=c5.classes[token.index == element.tokenIndex and frameElementName == element.name])

                    # jaunais variants: iet cauri visiem freimiem
                    if mode == 'new':
                        for frame in sentence.frames:
                            for element in frame.elements:
                                if element.name == frameElementName:
                                    for token in sentence.tokens:
                                        # fff = None
                                        # if token.index == element.tokenIndex:
                                        #     fff = frame
                                        # c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                                        #     frame=fff, _class=c5.classes[token.index == element.tokenIndex])
                                        #     # frame=frame, _class=c5.classes[token.index == element.tokenIndex])

                                        for ftoken in sentence.tokens:
                                            c5(token=token, tokens=sentence.tokens, elementName=frameElementName, 
                                                frame=ftoken, _class=c5.classes[token.index == element.tokenIndex and ftoken.index == frame.tokenIndex])
                                            # frame=frame, _class=c5.classes[token.index == element.tokenIndex])

                    # for token in sentence.tokens:
                    #     # c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                    #     #     frame=None, _class=c5.classes[0])
                    #     for ftoken in sentence.tokens:
                    #         c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                    #             frame=ftoken, _class=c5.classes[0])

                    # for token in sentence.tokens:
                    #     c5(token=token, tokens=sentence.tokens, elementName=frameElementName,
                    #         frame=None, _class=c5.classes[0])

                    # def rulefilter(..., forClassName="...")
                    # rules = []
                    # if ...:
                    #   rules.append((class, cover, ok, rulestring))
                    # if defaultClassName == class:
                    #   rules.append((class, cover, ok, "default"))
                    #
                    # return rules



            print('runing c5 ... ', end='')
            sys.stdout.flush()
            c5.run()

        print('loading rules ... ', end='')
        sys.stdout.flush()
        c5.loadRules()

        print('generating rules ... ', end='')
        sys.stdout.flush()
        # print('def FrameElement_', frameElementName, '(', ', '.join(feature.name for feature in frameElementFeatures), ', forClassName="YES"):', sep='', file=f)
        print('def FrameElement_', frameElementName, '(', ', '.join(feature.name for feature in frameElementFeatures), '):', sep='', file=f)
        c5.generate(indent=4, file=f)

        print('ok')
        sys.stdout.flush()

    print()


    print(file=f)
    print(file=f)
    print('frameTypeFunctions = {}', file=f)
    for frameType in sorted(frameTypesWithElementNames):
        print('frameTypeFunctions["'+frameType+'"] = FrameType_'+frameType+'', file=f)
    print(file=f)


    print('frameElementFunctions = {}', file=f)
    for frameElementName in sorted(frameElementNames):
        print('frameElementFunctions["'+frameElementName+'"] = FrameElement_'+frameElementName+'', file=f)
    print(file=f)


    print(templates.main, file=f)

    f.close()



# def getFeaturesDir():
#     import features
#     features.__file__


import platform

# pagaidām tikai šie divi
# TODO: compile for linux and uncomment this
# if 'Ubuntu-12' in platform.platform():
#     command = "bin/linux/c5.0"
if 'Darwin-12.5.0-x86_64-i386-64bit' in platform.platform():
    command = "bin/osx/c5.0"



# Summary:
# - dažādu datu ģenerācijas parametru izvēle
# - dažādu rules failu šablonu izvēle

# rules failā ir sekojoši šabloni:
# - head
# - frames & elements arrays
# - frame rules
# - element rules
# - body

# gmode = len(sys.argv) > 1 and sys.argv[1].startswith('g') and sys.argv[1] or ''



# TODO: šeit vajag paralelizāciju !!!!
# tad vajag izmantot vienus un tos pašus treniņdatus, šobrīd tiek padoti ceļi



trainPaths = ['../SemanticAnalyzer/SemanticData/Corpora/json/parsera_sintakse/*.json', '../SemanticAnalyzer/SemanticData/Corpora/json/manuaala_sintakse/*.json']
trainPaths = ['./train_reparsed/*/*.json', './train_reparsed/parsera_sintakse/*/*.json']

# compute distances pārbaude
# import loader
# print('Loading train data:')
# for document in loader.loadDocumentsFromPaths(trainPaths, sys.stderr, True):
#     pass
# quit()

# blackBox(trainPaths, filename='rulesbig100f4.py', features='features4', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f4', costs=100)
blackBox(trainPaths, filename='rulesbig100f4.py', features='features4', runC5Targets=False, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f4', costs=100)
# blackBox(trainPaths, filename='rulesbig100f4.py', features='features4', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f4', costs=100)


quit()

# blackBox(trainPaths, filename='rulesbig100f3_2.py', features='features3', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f3', costs=100)
blackBox(trainPaths, filename='rulesbig100f3_2.py', features='features3', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f3', costs=100)

quit()

# blackBox(trainPaths, filename='rulesbig100f4.py', features='features4', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f4', costs=100)
blackBox(trainPaths, filename='rulesbig100f4.py', features='features4', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f4', costs=100)

# blackBox(trainPaths, filename='rulesbig200f4.py', features='features4', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig200f4', costs=200)
blackBox(trainPaths, filename='rulesbig200f4.py', features='features4', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig200f4', costs=200)

# blackBox(trainPaths, filename='rulesbig100f3.py', features='features3', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f3', costs=100)
# blackBox(trainPaths, filename='rulesbig100f3.py', features='features3', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f3', costs=100)
# blackBox(trainPaths, filename='rulesbig100f3limit.py', features='features3', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig100f3', costs=100)

# blackBox(trainPaths, filename='rulesbig200f3.py', features='features3', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig200f3', costs=200)
# blackBox(trainPaths, filename='rulesbig200f3.py', features='features3', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig200f3', costs=200)
# blackBox(trainPaths, filename='rulesbig200f3limit.py', features='features3', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='perframetarget', tmpdir='tmpbig200f3', costs=200)

# ------------

# blackBox(trainPaths, filename='rulesbig100new.py', features='features2', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='simple', tmpdir='tmpbig100new', costs=100)
# blackBox(trainPaths, filename='rulesbig100new.py', features='features2', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='simple', tmpdir='tmpbig100new', costs=100)

# blackBox(trainPaths, filename='rulesbig200new.py', features='features2', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='simple', tmpdir='tmpbig200new', costs=200)
# blackBox(trainPaths, filename='rulesbig200new.py', features='features2', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='simple', tmpdir='tmpbig200new', costs=200)


# old
# blackBox(trainPaths, filename='rulesbig100.py', features='featuresg', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='simple', tmpdir='tmpbig100', costs=100)
# blackBox(trainPaths, filename='rulesbig100.py', features='featuresg', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='simple', tmpdir='tmpbig100', costs=100)

# blackBox(trainPaths, filename='rulesbig200.py', features='featuresg', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='simple', tmpdir='tmpbig200', costs=200)
# blackBox(trainPaths, filename='rulesbig200.py', features='featuresg', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='simple', tmpdir='tmpbig200', costs=200)

quit()


if gmode:
    if gmode == 'g0':
        # šajā modē abi runC5 ir False, jo izmanto jau gatavos ieejas datus no tmpg0 mapes
        blackBox('traing/sum.json', filename='rules'+gmode+'.py', features='featuresg0', tmpdir='tmpg0',
                runC5Targets=False, runC5Elements=False, command=command, mode='simple', allSentences=False)
    if gmode == 'g1':
        blackBox('traing/sum.json', filename='rules'+gmode+'.py', features='featuresg', tmpdir='tmp'+gmode,
                runC5Targets=True, runC5Elements=True, command=command, mode='simple', allSentences=False)
    if gmode == 'g2':
        blackBox('traing/sum.json', filename='rules'+gmode+'.py', features='featuresg', tmpdir='tmp'+gmode,
                runC5Targets=True, runC5Elements=True, command=command, mode='simple', allSentences=True, costs=100)
    if gmode == 'g3':
        blackBox(trainPaths, filename='rules'+gmode+'.py', features='featuresg', tmpdir='tmp'+gmode,
                runC5Targets=True, runC5Elements=True, command=command, mode='simple', allSentences=False)
    if gmode == 'g4':
        blackBox(trainPaths, filename='rules'+gmode+'.py', features='featuresg', tmpdir='tmp'+gmode,
                runC5Targets=True, runC5Elements=True, command=command, mode='simple', allSentences=True)
    # if gmode.endswith('m'):
    if 'm' in gmode:
        print("Autogeneration would replace manually tuned, edit by hand please and pipe with ./pipe.py g[...]m")
else:
    blackBox('traing/sum.json', runC5Targets=True, runC5Elements=True, allSentences=True, command=command, mode='new')
    # blackBox('traing/sum.json', runC5Targets=False, runC5Elements=True, allSentences=True, command=command, mode='new')
    # blackBox('traing/sum.json', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='new')
    # blackBox('traing/sum.json', runC5Targets=False, runC5Elements=False, allSentences=True, command=command, mode='new')




