#!/usr/bin/env python3

import os, json
from utils import Dict



class RulesOperator:

    def __init__(self, features, rules, namedLists):
        self.features = features
        self.rules = rules
        self.namedLists = namedLists

    def __call__(self, *args, **kargs):
        # konvertē no ievaddatiem uz pazīmju datiem (ievaddati ir token=..., tokens=... utt.), pazīmju dati: NLEMMA=..., LEMMA=..., ...
        namedFeatureValues = self.features(*args, **kargs)
        # iet cauri likumiem un atgriež True/False

        for rule in self.rules:

            match = True
            for condition in rule.conditions:

                if condition.name in namedFeatureValues:
                    if condition.op == '==':
                        if namedFeatureValues[condition.name] != condition.value:
                            match = False
                    elif condition.op == 'in':
                        if conditon.list and condition.list in self.namedLists:
                            if namedFeatureValues[condition.name] not in self.namedLists[condition.list]:
                                match = False
                        elif condition.value:
                            if namedFeatureValues[condition.name] not in condition.value:
                                match = False
                    elif condition.op == '<=':
                        if namedFeatureValues[condition.name] > condition.value:
                            match = False
                    elif condition.op == '>':
                        if namedFeatureValues[condition.name] <= condition.value:
                            match = False
                    elif condition.op == '<':
                        if namedFeatureValues[condition.name] >= condition.value:
                            match = False
                    elif condition.op == '>=':
                        if namedFeatureValues[condition.name] < condition.value:
                            match = False
                    elif condition.op == '!=':
                        if namedFeatureValues[condition.name] == condition.value:
                            match = False
                    else:
                        # unknown operation, default
                        match = False
                else:
                    match = False

                if not match:
                    break
                
            # TODO: te var atgriezt arī pašu likumu, lai varētu zināt apastākļus (cover/ok utt.)
            if match:
                return rule.value

        # default
        return False



class RulesDB:

    def __init__(self, features, name='', filesystem='', filename=None):
        self.features = features

        self.rulesByName = {}
        self.namedLists = {}

        if filename == None:
            if name and filesystem:
                self.name = name
                self.filename = os.path.join(filesystem, name+'.json')
                dirname = os.path.dirname(self.filename)
                if dirname and not os.path.isdir(dirname):
                    os.makedirs(dirname)
        else:
            self.filename = filename
            self.load()

        def type2str(t):
            if t == int:
                return 'int'
            if t == str:
                return 'str'
            return ''
        self.header = [Dict(name=feature.name, type=type2str(feature.type)) for feature in self.features]

        self.rulesOperatorsByName = {}

    def load(self):
        filename = self.filename
        with open(filename) as f:
            data = json.load(f, object_hook=Dict)
            self.header = data.features
            self.rulesByName = data.rulesByName
            self.name = data.name
            self.namedLists = data.namedLists

    def save(self):
        filename = self.filename
        with open(filename, 'w') as f:
            # NOTE: ja faila nosaukumam vajag citu name, tad šeit var uzstādīt pēc instances izveidošanas
            json.dump(Dict(name=self.name, features=self.header, rulesByName=self.rulesByName, namedLists=self.namedLists),
                    f, indent=4, sort_keys=True)

    def __getitem__(self, name):
        return self.rulesByName[name]

    def __setitem__(self, name, value):
        self.rulesByName[name] = value


    def __call__(self, name):

        if name not in self.rulesOperatorsByName:
            if name not in self.rulesByName[name]:
                def empty(self, *args, **kargs):
                    return False
                self.rulesOperatorsByName[name] = empty
            self.rulesOperatorsByName[name] = RulesOperator(self.features, self.rulesByName[name], self.namedLists)

        return self.rulesOperatorsByName[name]


class CombinedRulesDB:

    def __init__(self, filename, targetFeatures, elementFeatures):
        self.filename = filename
        self.targetFeatures = targetFeatures
        self.elementFeatures = elementFeatures
        self.load()

    def load(self):
        filename = self.filename
        with open(filename) as f:
            data = json.load(f, object_hook=Dict)

            self.namedLists = data.namedLists
            self.targetRules = RulesDB(self.targetFeatures)
            self.targetRules.namedLists = data.namedLists
            self.targetRules.rulesByName = data.targetRulesByType

            self.namedLists = data.namedLists
            self.elementRules = RulesDB(self.elementFeatures)
            self.elementRules.namedLists = data.namedLists
            self.elementRules.rulesByName = data.elementRulesByName

    # TODO: te vajag metodi ģenerēt pyton šablonu: rules.py



def saveCombined(targetRulesDB, elementRulesDB, filesystem='', filename='all.json', frameNET=None):

    output = Dict(name='all', )
    if frameNET:
        output.frameNET = frameNET

    namedLists = {}
    for name, value in targetRulesDB.namedLists.items():
        namedLists[name] = value
    for name, value in elementRulesDB.namedLists.items():
        namedLists[name] = value
    output.namedLists = namedLists

    output.targetFeatures = targetRulesDB.header
    output.elementFeatures = elementRulesDB.header
    output.targetRulesByType = targetRulesDB.rulesByName
    output.elementRulesByName = elementRulesDB.rulesByName

    filename = os.path.join(filesystem, filename)
    with open(filename, 'w') as f:
        json.dump(output, f, indent=4, sort_keys=True)

