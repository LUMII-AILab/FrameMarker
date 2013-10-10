#!/usr/bin/env python3

# TODO: update sys.path to point to featuresclass

from featuresclass import Features

# neesošas vērtības placeholderis
NONE = "[NONE]"

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
def POS(token, tokens):
    return normalizeTag(token.tag)

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
def LEMMA(token, tokens, elementName, frame):
    return token.lemma

@frameElementFeatures.feature
def POS(token, tokens, elementName, frame):
    return normalizeTag(token.tag)

@frameElementFeatures.feature
def HLEMMA(token, tokens, elementName, frame):
    if not token.parent:
        return NONE
    return token.parent.lemma

@frameElementFeatures.feature
def HPOS(token, tokens, elementName, frame):
    if not token.parent:
        return NONE
    return normalizeTag(token.parent.tag)

@frameElementFeatures.feature
def TARGET_LEMMA(token, tokens, elementName, frame):
    # return NONE
    if frame:
        # return frame.type
        # return tokens[frame.tokenIndex].lemma
        return frame.lemma
    return NONE


