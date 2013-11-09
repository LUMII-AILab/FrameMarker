#!/usr/bin/env python
# coding=utf-8
# for Python 2 compatibility

# TODO: update sys.path to point to featuresclass

from featuresclass import Features

# neesošas vērtības placeholderis
NONE = "[NONE]"
# NONE = None
# NONE = ""

#
# Prolog morfoloģiskā taga normalizēšana no DEDIC26bGGG9m.pl:
#
# bree(A,B) :- atom_chars(A,AA),bre(AA,BB),atom_chars(B,BB).
# 
# bre([n,NTIPS,DZIMTE,SKAITLIS,LOC|_],[n,LOC]) :- !.
# bre([v,VTIPS,ATGRIEZ,p,LOKAMIBA,DZIMTE,SKAITLIS,LOC,KARTA,LAIKS,NOTEIKTIBA|_],[v,VTIPS,ATGRIEZ,p,KARTA]) :- !.
# bre([v,VTIPS,ATGRIEZ,IZTEIKSME,LAIKS,TRANZIT,KONJUGAC,PERS,SKAITLIS,KARTA,NOLIEGUMS|_],[v,VTIPS,ATGRIEZ,IZTEIKSME,KARTA]) :- !.
# bre([a,ATIPS,DZIMTE,SKAITLIS,LOC,NOTEIKTIBA,PAKAPE|_],[a]) :- !.
# bre([p,VVTIPS,PERS,DZIMTE,SKAITLIS,LOC,NOLIEGUMS|_],[p,LOC]) :- !.
# bre([m,SKTIPS,UZBUVE,DZIMTE,SKAITLIS,LOC|_],[m]) :- !.
# bre([z,PZTIPS|_],[z]) :- !.
# bre([r,PAKAPE,GRUPA|_],[r]) :- !. 
# bre([c,SAIKLATIPS,UZBUVE|_],[c]) :- !.
# bre([q|_],[q]) :- !. % partikula
# bre([Z|_],[Z]) :-  member(Z,[i,x,y]), !. % izsauksmes vards, kodifikators, ???
# bre([s|_],[s]) :- !. % start un stop root nodes
# bre(P,[f]). % :- writeln(['debug bre:',P]). viss parejais
#
# Python ekvivalents:
#
def normalizeTag(tag):
    if not tag:
        return 'f'
    if tag[0] == 'n':
        return tag[0]+tag[4]
    elif tag[0] == 'v' and tag[3] == 'p':
        return tag[0]+tag[1:4]+tag[8]
    elif tag[0] == 'v':
        return tag[0:4]+tag[9]
    elif tag[0] == 'p':
        return tag[0]+tag[5]
    elif tag[0] in 'amzrcqixys':
        return tag[0]
    return 'f'



# Pazīmju definēšana freimu targetiem

frameTargetFeatures = Features()
# just in case
frameTargetFeatures.NONE = NONE

@frameTargetFeatures.feature
def PLEMMA(token, tokens):
    return tokens[token.index - 1].lemma

@frameTargetFeatures.feature
def LEMMA(token, tokens):
    return token.lemma

@frameTargetFeatures.feature
def LETA_LEMMA(token, tokens):
    if token.features and token.features.leta_lemma:
        return token.features.leta_lemma
    return NONE

@frameTargetFeatures.feature
def POS(token, tokens):
    return normalizeTag(token.tag)

@frameTargetFeatures.feature
def NETYPE(token, tokens):
    if token.namedEntityType:
        return token.namedEntityType
    return NONE

@frameTargetFeatures.feature
def NLEMMA(token, tokens):
    if token.index + 1 < len(tokens):
        return tokens[token.index + 1].lemma
    return NONE
    # return '[END]'



# Pazīmju definēšana freimu elementiem

frameElementFeatures = Features()
# just in case
frameElementFeatures.NONE = NONE
                    
# NOTE: funkciju nosaukumos var būt par kādu mainīgo mazāk, bet ne vairāk kā sekojošie:
# OUTDATED: token, tokens, elementName, targetTokenIndices [set of frame target token indices for current element name]

@frameElementFeatures.feature
def LEMMA(token, tokens, elementName):
    return token.lemma

@frameElementFeatures.feature
def LETA_LEMMA(token, tokens, elementName):
    if token.features and token.features.leta_lemma:
        return token.features.leta_lemma
    return NONE

@frameElementFeatures.feature
def POS(token, tokens, elementName):
    return normalizeTag(token.tag)

@frameElementFeatures.feature
def NETYPE(token, tokens):
    if token.namedEntityType:
        return token.namedEntityType
    return NONE

@frameElementFeatures.feature
def HLEMMA(token, tokens, elementName):
    if not token.parent:
        return NONE
    return token.parent.lemma

@frameElementFeatures.feature
def HLETA_LEMMA(token, tokens, elementName):
    if token.parent and token.features and token.features.leta_lemma:
        return token.features.leta_lemma
    return NONE

@frameElementFeatures.feature
def HPOS(token, tokens, elementName):
    if not token.parent:
        return NONE
    return normalizeTag(token.parent.tag)

@frameElementFeatures.feature
def HNETYPE(token, tokens):
    if token.parent and token.parent.namedEntityType:
        return token.namedEntityType
    return NONE

@frameElementFeatures.feature
def TARGET_TYPE(token, tokens, frame):
    return frame.type

updown = {}
updown[False] = 'D'
updown[True] = 'U'

@frameElementFeatures.feature
def TARGET_PATH(token, tokens, frame):
    return ''.join(updown[n[1]] for n in token.distances[frame.tokenIndex]) or 'N'

@frameElementFeatures.feature
def TARGET_PATH_SHORT(token, tokens, frame):
    prev = None
    path = []
    for n in token.distances[frame.tokenIndex]:
        if n[1] != prev:
            path.append(n[1])
            prev = n[1]
    return ''.join(updown[n] for n in path) or 'N'

NEWS_left = {}
NEWS_right = {}
NEWS_left[True] = 'N'
NEWS_left[False] = 'W'
NEWS_right[True] = 'E'
NEWS_right[False] = 'S'

# N E W S
@frameElementFeatures.feature
def TARGET_PATH2D(token, tokens, frame):
    if not token.distances:
        return '_'
    path = ''
    fromIndex = token.index
    for n in token.distances[frame.tokenIndex]:
        toIndex = n[0]
        if toIndex < fromIndex:
            path += NEWS_left[n[1]]
        else:
            path += NEWS_right[n[1]]
        fromIndex = n[0]
    return path

# N E W S short:
@frameElementFeatures.feature
def TARGET_PATH2D_SHORT(token, tokens, frame):
    if not token.distances:
        return '_'
    path = ''
    fromIndex = token.index
    prev = ''
    for n in token.distances[frame.tokenIndex]:
        toIndex = n[0]
        if toIndex < fromIndex:
            c = NEWS_left[n[1]]
        else:
            c = NEWS_right[n[1]]
        if c != prev:
            path += c
        prev = c
        fromIndex = n[0]
    return path

@frameElementFeatures.feature('continuous')
def TARGET_DIST(token, tokens, frame):
    return len(token.distances[frame.tokenIndex])

