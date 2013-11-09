#!/usr/bin/env python3

import sys
from utils import Dict

# Latviešu alfabēts:
# āĀēĒšŠžŽčČģĢņŅūŪīĪķĶļĻ
# āēšžčģņūīķļ
transtable = (
    ("ā", "a"),
    ("ē", "e"),
    ("ī", "i"),
    ("ū", "u"),
    ("č", "c"),
    ("ķ", "k"),
    ("ļ", "l"),
    ("ģ", "g"),
    ("ņ", "n"),
    ("š", "s"),
    ("ž", "z")
)

def normalize(s):
    s = s.lower()
    for cin, cout in transtable:
        s = s.replace(cin, cout)
    return s
 

# convert extended features from string name1=val1|name2=val2|... to dictionary Dict(name1=val1, name2=val2, ...)
# NOTE: names will be translated to lovercase and stripped from latvian specific symbols to be usable as attribute names: .name
def convertExtendedFeatures(extendedFeatures):
    extendedFeaturesDict = Dict()
    # NOTE: nedaudz dīvains veinds kā apstrādāt gadījumus, kur val sakrīt ar "=", t.i., name1==|name2=val2|...
    # for k,v in (f.split('=') for f in features.split('|')):
    for kv in extendedFeatures.split('|'):
        kv = kv.split('=')
        k = kv[0]
        if len(kv) == 2:
            v = kv[1]
        elif len(kv) > 2:
            v = '='
        k = normalize(k)
        extendedFeaturesDict[k] = v
    return extendedFeaturesDict


def tokensToText(tokens):

    # TODO: kur iedaras ‘ un ’ ?
    quoteSymbols = ["'", '"']
    noGapBefore = [',', ':', ';', '.', '!', '?', '%', ')', ']', '}', '»'];
    noGapAfter = ['(', '[', '{', '«'];

    def gap(prev, next, quotes):
        if not prev and next.lemma in quoteSymbols:
            quotes[next.lemma] = not quotes.get(next.lemma, False)
        if not prev or prev.lemma in noGapAfter or next.lemma in noGapBefore:
            return ''
        if next.lemma in quoteSymbols:
            quoted = quotes.get(next.lemma, False)
            quotes[next.lemma] = not quotes.get(next.lemma, False)
            if quoted:
                return ''
        if prev.lemma in quoteSymbols:
            if quotes.get(prev.lemma, False):
                return ''
        return ' '

    text = ''
    prev = None
    quotes = {}

    for token in tokens:
        text += gap(prev, token, quotes)
        text += token.form
        prev = token

    return text


def parseCoNLL(data):

    if type(data) == str:
        lines = data.split('\n')
    else:
        lines = data

    def createSentence(tokens):
        # text = ' '.join(token.form for token in tokens)
        sentence = Dict(tokens=tokens, text=tokensToText(tokens))
        return sentence

    def createToken(line):
        parts = line.split('\t')
        token = Dict(index=int(parts[0]), form=parts[1], lemma=parts[2], pos=parts[3], tag=parts[4])
        if parts[6] == '_':
            token.parentIndex = -1
        else:
            token.parentIndex = int(parts[6])
        extendedFeatures = parts[5]
        if extendedFeatures and extendedFeatures != '_':
            # NOTE: šis tiks veikts vēlāk
            # token.extendedFeatures = convertExtendedFeatures(extendedFeatures)
            token.extendedFeatures = extendedFeatures
        # kas ir pēc parentIndex ?
        # namedEntityID vai namedEntityType ?
        if len(parts) == 8:
            token.namedEntityType = parts[7]
        elif len(parts) == 9:
            token.namedEntityID = parts[7]
            token.namedEntityType = parts[8]
        if len(parts) > 7:
            if token.namedEntityID == '_':
                token.namedEntityID = None
            if token.namedEntityType == '_' or token.namedEntityType == 'O':
                # NOTE: ja šeit ir vēlams O, tad vajag nokomentēt iepriekšējo rindu sākot ar "or"
                token.namedEntityType = None

        return token

    tokens = []
    sentences = []
    for line in lines:
        line = line.rstrip()
        if not line:
            sentences.append(createSentence(tokens))
            tokens = []
        else:
            tokens.append(createToken(line))
    # nedrīkst pazaudēt pēdējo teikumu (ja gadījumā nebeidzas ar tukšu rindu
    if tokens:
        sentences.append(createSentence(tokens))
    return sentences


# TODO: vajag funkciju, kas pārbauda datu pareizību: tokenu skaitu, indeksu secību, parent indexus,
# vai freimiem un to elementiem ir atbilstoši tokeni utt.
# Ja nav frames, tad ir jāpievieno kaut vai tukšs frames=[]

def linkSentence(sentence):
    # cleanup old links if present
    for token in sentence.tokens:
        del token.parent
        del token.children
    # link parents with childrens
    for token in sentence.tokens:
        if token.parentIndex >= 0:
            parent = sentence.tokens[token.parentIndex]
            if parent.children is None:
                parent.children = []
            parent.children.append(token)
            token.parent = parent

def unlinkSentence(sentence):
    # cleanup links if present
    for token in sentence.tokens:
        del token.parent
        del token.children

# TODO: vajag labāku compute distances funkcijas implementāciju, kas nav rekursīva !!!
# izveido struktūru, kas satur ceļus no tokeniem līdz tokeniem pa sintakses koku
def computeDistances(sentence):

    def travel(stack=None, distances=None):

        if distances == None:
            distances = {}

        last = None

        if type(stack) != tuple:
            current = stack
            stack = ((stack.index,),)
        else:
            # apstrādā tekošo, papildina distances
            current = sentence.tokens[stack[-1][0]]
            last = sentence.tokens[stack[-2][0]]

            distances[current.index] = stack[1:]
            # convert to more convenient structure
            # distances[current.index] = tuple(NextNode(*entry) for entry in stack[1:])
            # distances[current.index] = tuple(Dict(index=entry[0], parent=entry[1]) for entry in stack[1:])

        # iet parent virzienā un children virzienā
        if current.parent and current.parent != last:
            travel(stack + ((current.parent.index,True),), distances)
        if current.children:
            for child in current.children:
                if child == last:
                    continue
                travel(stack + ((child.index,False),), distances)

        return distances

    # Algoritms: pārstaigā visus tokenus un skatās gan uz parent pusi, gan uz child pusi
    for token in sentence.tokens:
        token.distances = travel(token)


def prepareSentence(sentence, shouldComputeDistances=False):

    # add root token if needed
    if len(sentence.tokens) == 0 or sentence.tokens[0].index > 0:
        sentence.tokens.insert(0, Dict(index=0, tag="R", pos="R", lemma="[*]", form="[*]", parentIndex=-1, features=Dict()))

    linkSentence(sentence)

    if shouldComputeDistances:
        computeDistances(sentence)


# nokopē teikuma objektu nodzēšot freimus
def copySentence(sentence):
    copy = Dict(sentence)
    copy.frames = []
    return copy


# sagatavo teikumu saglabāšanai failā
def cleanSentence(sentence):
    # dzēš root tokenu
    if sentence.tokens[0].index == 0:
        sentence.tokens.pop(0)
    # dzēš pārējās datu struktūras, kurām nav jābūt failos
    for token in sentence.tokens:
        del token.parent
        del token.children
        del token.distances
        del token.namedEntityType
        # pārveido pazīmes atpakaļ no Dict struktūras uz stringu name1=value1|name2=value2|...
        if type(token.features) == dict or type(token.features) == Dict:
            token.features = '|'.join('='.join(item) for item in token.features.items())
    return sentence


def compareSentences(silverSentence, goldSentence, compareTokens=True, file=sys.stderr):

    # šo daļu var izlaist, ja ir zināms, ka teikumu tokeni sakrīt
    if compareTokens:
        if len(silverSentence.tokens) != len(goldSentence.tokens):
            print('WARNING: sentences differ', file=file)
            return 0.0, 0, 0

        def compare(token1, token2):
            return token1.form == token2.form and token1.lemma == token2.lemma and token1.tag == token2.tag

        for token1,token2 in zip(silverSentence.tokens, goldSentence.tokens):
            if not compare(token1, token2):
                print('WARNING: sentences differ', file=file)
                return 0.0, 0, 0
    
    def add(sset,item,copy=0):
        if (copy,)+item in sset:
            add(sset,item,copy+1)
        else:
            sset.add((copy,)+item)


    gold = set()
    silver = set()
    if goldSentence.frames is not None:
        for frame in goldSentence.frames:
            for element in frame.elements:
                add(gold,(frame.tokenIndex,frame.type,element.tokenIndex,element.name))
    if silverSentence.frames is not None:
        for frame in silverSentence.frames:
            for element in frame.elements:
                add(silver,(frame.tokenIndex,frame.type,element.tokenIndex,element.name))

    valid_count = float(len(silver & gold))
    total_count = float(len(silver | gold))

    if total_count == 0:
        if valid_count == 0:
            # print('WARNING: zero expected, zero got, assuming 100% coincidence!', file=file)
            return 1.0, 0, 0    # šeit nav nekāda total ieguldījuma, tādēļ WARNINGs nav nepieciešams
        return 0.0, 0, 0

    # šeit true skaits nav jādivkāršo, jo & operācija ar python set() objektiem jau izslēdz dublikātus (tādēļ arī nepieciešama add() funkcija)
    return float(valid_count) / float(total_count), valid_count, total_count


def scoreSentences(sentences, markSentenceFunction, verbose=False, file=sys.stdout):

    if not markSentenceFunction:
        print('ERROR: no frame marker function specified!', file=file)
        return None, None, None

    print('Scoring: ', end='', file=file)
    valid_sum = 0
    total_sum = 0
    for sentence in sentences:
        gold = sentence
        silver = markSentenceFunction(copySentence(sentence))
        score, valid, total = compareSentences(silver, gold, False)
        valid_sum += valid
        total_sum += total
        if verbose:
            if valid == 0 and total == 0:
                # print('()', end='', file=file, flush=True)    # requires Python 3.3
                print('()', end='', file=file)
                file.flush()
            else:
                # print(str(int(score*100))+'%', end='', file=file, flush=True)    # requires Python 3.3
                print(str(int(score*100))+'%', end='', file=file)
                file.flush()
        else:
            # print('.', end='', file=file, flush=True)    # requires Python 3.3
            print('.', end='', file=file)
            file.flush()

    print('DONE', file=file)

    total_score = float(valid_sum)/float(total_sum)
    # print('Total score:', str(int(total_score*100))+'%', file=file, flush=True)    # requires Python 3.3
    print('Total score:', str(int(total_score*100))+'%', file=file)
    file.flush()

    return total_score, valid_sum, total_sum

def outputSentence(sentence, file=sys.stdout):
    print('\tSentence:', file=file)
    print('\t', ' '.join((str(token.parentIndex)+'->['+str(token.index)+']'+token.form for token in sentence.tokens)), file=file)
    print('\tFrames:', file=file)
    for frame in (x for x in sentence.frames if x.tokenIndex > 0):
        print('\t\t', frame.type, '\t\t', '['+str(frame.tokenIndex)+']:', sentence.tokens[frame.tokenIndex].form, file=file)
        for element in (x for x in frame.elements if x.tokenIndex > 0):
            print('\t\t', rame.type+'|'+element.name, '\t', '['+str(element.tokenIndex)+']:', sentence.tokens[element.tokenIndex].form, file=file)

def convertSentenceExtendedFeatures(sentence):
    for token in sentence.tokens:
        if token.features and type(token.features) == str:
            token.features = convertExtendedFeatures(token.features)

# Tālāk ir convenience funkcijas, kas darbojas ar teikumu masīviem

def linkSentences(sentences):
    for sentence in sentences:
        linkSentence(sentence)

def unlinkSentences(sentences):
    for sentence in sentences:
        unlinkSentence(sentence)

def prepareSentences(sentences, shouldComputeDistances=False):
    for sentence in sentences:
        prepareSentence(sentence, shouldComputeDistances)

def cleanSentences(sentences):
    for sentence in sentences:
        cleanSentence(sentence)

def removeFramesFromSentences(sentences):
    for sentence in sentences:
        sentence.frames = [];

def outputSentences(sentences, file=sys.stdout):
    for sentence in sentences:
        outputSentence(sentence, file=file)

def convertSentencesExtendedFeatures(sentence):
    for sentence in sentences:
        convertSentenceExtendedFeatures(sentence)

def cleanDocument(document):
    for sentence in document.sentences:
        cleanSentence(sentence)


def prepareDocument(document, shouldComputeDistances=False):

    if not document or type(document) != Dict:
        return

    # link named entity types
    if document.namedEntities:
        namedEntities = document.namedEntities
        for sentence in document.sentences: 
            for token in sentence.tokens:
                if token.namedEntityID != None:
                    if token.namedEntityID in namedEntities:
                        token.namedEntityType = namedEntities[token.namedEntityID].type

    for sentence in document.sentences: 

        if sentence.frames is None:
            sentence.frames = []

        prepareSentence(sentence, shouldComputeDistances)

        for token in sentence.tokens:

            if token.features and type(token.features) == str:
                token.features = convertExtendedFeatures(token.features)


def loadDocument(data, shouldComputeDistances=False):

    if type(data) == str: # string

        import json, os

        if os.path.isfile(data): # filename
            try:
                with open(data) as f:
                    document = json.load(f, object_hook=Dict)
                    if 'tokens' in document:
                        document = Dict(sentences=[document])
            except ValueError:
                with open(data) as f:
                    document = parseCoNLL(f.read())
        else: # data
            try:
                document = json.loads(data, object_hook=Dict)
                if 'tokens' in document:
                    document = Dict(sentences=[document])
            except ValueError:
                document = parseCoNLL(data)

    elif type(data) == dict or type(data) == Dict:

        if 'sentences' in data:
            document = data
        elif 'tokens' in data:
            document = Dict(sentences=[document])

    elif hasattr(data, 'read'): # maybe file-like ?

        import json

        f = data
        data = f.read()
        f.close()
        try:
            document = json.loads(data, object_hook=Dict)
        except ValueError:
            document = parseCoNLL(data)



    if not document:
        return None

    # only sentences
    if type(document) == list:
        document = Dict(sentences=document)

    prepareDocument(document, shouldComputeDistances)

    return document


def loadSentences(data, shouldComputeDistances=False):
    document = loadDocument(data, shouldComputeDistances)
    if not document:
        return []
    return document.sentences


def getFrameTypesWithElementNames(sentences, frameTypesWithElementNames={}):

    for sentence in sentences:
        # link sentence
        linkSentence(sentence)
        # extract frame types and element names
        if sentence.frames:
            for frame in sentence.frames:
                if frame.type not in frameTypesWithElementNames:
                    frameTypesWithElementNames[frame.type] = set()
                for element in frame.elements:
                    frameTypesWithElementNames[frame.type].add(element.name)

    return frameTypesWithElementNames


def pathIterator(paths, basedir=''):

    import glob, os

    if type(paths) == str:
        paths = [paths]

    for path in paths:
        path = os.path.expanduser(path)
        if not os.path.isabs(path):# and not os.path.isfile(path):
            if basedir:
                path = os.path.join(basedir, path)
            path = os.path.abspath(path)

        for path in glob.iglob(path):
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if not os.path.isfile(path):
                continue
            yield path


def loadSentencesFromPaths(paths):
    for path in pathIterator(paths):
        for sentence in loadSentences(path):
            yield sentence

def loadDocumentsFromPaths(paths, file=None, shouldComputeDistances=False):
    for path in pathIterator(paths):
        if file:
            print(path, file=file)
        yield loadDocument(path, shouldComputeDistances)


if __name__ == "__main__":

    # Test tokensToText
    tokens = []
    tokens.append(Dict(form='Jānis', lemma='Jānis'))
    tokens.append(Dict(form='saka', lemma='saka'))
    tokens.append(Dict(form=':', lemma=':'))
    tokens.append(Dict(form='"', lemma='"'))
    tokens.append(Dict(form='drīz', lemma='drīz'))
    tokens.append(Dict(form='līs', lemma='līst'))
    tokens.append(Dict(form=',', lemma=','))
    tokens.append(Dict(form='jo', lemma='jo'))
    tokens.append(Dict(form='ir', lemma='ir'))
    tokens.append(Dict(form='mākoņains', lemma='mākoņains'))
    tokens.append(Dict(form='!', lemma='!'))
    tokens.append(Dict(form='"', lemma='"'))
    print(tokensToText(tokens))
