#!/usr/bin/env python3

from utils import Dict

# Modulis atbild par treniņdatu datu ģenerēšanu no treniņfailiem (.json'iem)
# 
# API:
# Data objekts
# Tam pakārtoti Category objekti
# 
# Data(features, ...) : daudzpunktes vietā varētu būt storage ceļš/direktorija vai kas tāds
# Data.categories[name] = Category()
# Data.add(feature values)
# Category.add(value)

# In memory Datu klašu šabloni

# defaultā klase: in memory datubāze, saglabāšana varētu tikt realizēta teksta failos
class Data:

    # varbūt te labāk dirname ?
    def __init__(self, features, filename):
        self.features = features
        self.categories = {}        # by name: vai nu frame type vai element type
        self.filename = filename
        self.names = tuple(feature.name for feature in features)
        self.data = []

    # load/save
    def load(self):
        # TODO: save in text file
        # self.data = ...
        # TODO: te no kaut kurienes ir jāielādē saraksta ar kategorijām, kuras ielādēt
        # for name, category in self.categories.items():
        #     category.load()
        pass

    def save(self):
        # TODO: save in text file
        # rekursīvi izsauc kategoriju save
        for name, category in self.categories.items():
            category.save()
        # TODO: kaut kur ir jāsaglabā saraksts ar kategorijām
        pass

    def reset(self):
        for category in self.categories.values():
            category.reset()

    # darbības ar kategorijām

    #
    # datu ievade, izvade
    #

    # named -> indexed tuple
    def indexed(self, *featureValues, **namedFeatureValues):

        n = len(self.names)
        data = [None]*n

        if featureValues:
            data[:min(n, len(featureValues))] = featureValues[:min(n, len(featureValues))]

        for name, value in namedFeatureValues.items():
            try:
                data[self.names.index(name)] = value 
            except ValueError:
                pass

        return data


    def add(self, *args, **kargs):
        # konvertē no ievaddatiem uz pazīmju datiem (ievaddati ir token=..., tokens=... utt.), pazīmju dati: NLEMMA=..., LEMMA=..., ...
        self.addData(**self.features(*args, **kargs))

    def addData(self, *featureValues, **namedFeatureValues):
        data = self.indexed(*featureValues, **namedFeatureValues)
        index = len(self.data)
        self.data.append(data)
        return data

    # search
    def indexes(self, *featureValues, **namedFeatureValues):
        # meklējamo datu šablons, None laukus uzskata par relaksētiem
        # template = self.indexed(*featureValues, **namedFeatureValues)
        # for index in range(len(self.data)):
        #     data = self.data[i]
        #     match = True
        #     # salīdzina pa komponentēm
        #     for d,t in zip(data, template):
        #         if t is None:   # relaksēts parametrs
        #             continue
        #         if d != t:
        #             match = False
        #             break

        #     if match:
        #         yield index

        # alternatīvs variants būtu meklēt pēc nosaukumiem
        template = self.named(self.indexed(*featureValues, **namedFeatureValues))
        components = [(self.names.index(name),value) for name,value in template.items() if name in self.names]
        for index in range(len(self.data)):
            data = self.data[i]
            match = True
            for component in components:
                if data[component[0]] != component[1]:
                    match = False
                    break

            if match:
                yield index

        # end 

    def cover(self, rules):

        if type(rules) != list and type(rules) != tuple:
            rules = [rules]
        else:
            rules = list(rules) # kopē sarakstu, lai nebojātu oriģinālu

        for i in range(len(rules)):
            conditions = [(self.names.index(condition.name), condition.op, condition.value)
                    for condition in rules[i].conditions if condition.name in self.names]
            print(conditions)
            rules[i] = Dict(value=rules[i].value, conditions=conditions)

        for index in range(len(self.data)):
            data = self.data[index]
            match = True
            for rule in rules:
                for condition in rule.conditions:
                    if condition[1] == '==':
                        if data[condition[0]] != condition[2]:
                            match = False
                    elif condition[1] == '<=':
                        if data[condition[0]] > condition[2]:
                            match = False
                    elif condition[1] == '>':
                        if data[condition[0]] <= condition[2]:
                            match = False
                    elif condition[1] == 'in':
                        if data[condition[0]] not in condition[2]:
                            match = False
                    if not match:
                        break
                if match and rule.value == False and rule != rules[-1]:     # nav pēdējais, jo pēdējam mēs gribam saskaitīt
                    match = False
                if not match:
                    break

            if match:
                yield index



    def __iter__(self):
        return iter(self.data)


    def __len__(self):
        return len(self.data)


    # ko atgriež ? tuple vai dict ar key=value vērtībām ?
    # var darīt tā: atgriezt tuple (jo tas ir efektīvāk) un piedāvāt konvertoru uz kv dict
    def __getitem__(self, index):
        return self.data[index]

    def named(self, data):
        named = Dict()
        for name,value in zip(self.names, data):
            named[name] = value
        return named


class Category:

    def __init__(self, data, name='TestCategory', filename='TestCategory.dat'):
        self.data = data
        self.name = name
        self.filename = filename
        self.values = []

    def __getitem__(self, index):
        return self.values[index]

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def reset(self):
        pass

    # pievieno vērtību, atgriež indeksu (salīdzināšanai ?)
    def add(self, value):
        self.values.append(value)

    # dotajai klasei/kategorijai atgriež cover/ok vērtības
    # def cover(self, *featureValues, **namedFeatureValues):
    #     cover = 0
    #     ok = 0
    #     for index in self.data.indexes(*featureValues, **namedFeatureValues):
    #         cover +=1 
    #         value = self[index]
    #         if value:
    #             ok += 1
    #     return Dict(cover=cover, ok=ok)

    # vēl varētu viena likuma vietā filtrēt cauri vairākiem un tikai, ja rezultātā paliek pāri true (lai tiktu galā ar false)
    def cover(self, rules):
        if type(rules) != list and type(rules) != tuple:
            rules = [rules]
        cover = 0
        ok = 0
        for index in self.data.cover(rules):
            value = self[index]
            # if rule.value != value: pass
            expectedValue = rules[-1].value
            if value is not None:
                cover +=1 
                if value == expectedValue:
                    ok += 1
        return Dict(cover=cover, ok=ok)

    def load(self):
        pass

    def save(self):
        pass




# SQLite versijas, kas datus saglabā SQLite datubāzē

import sqlite3

class SQLiteData(Data):

    def __init__(self, features, filename):
        super().__init__(features, filename)

        # kura klase kā tieši izmanto filename ir implementācijas specifiska informācija
        if not self.filename.endswith('db3'):
            self.filename += '.db3'

        self.conn = sqlite3.connect(self.filename)
        self.cur = self.conn.cursor()

    def reset(self):
        def featureType(feature):
            if feature.type == int:
                return 'INTEGER'
            if feature.type == str:
                return 'TEXT'

        for category in self.categories.values():
            category.reset()

        # izveido datu tabulu
        self.cur.execute("DROP INDEX IF EXISTS data_index;")
        self.cur.execute("DROP TABLE IF EXISTS data;")
        self.conn.commit()

        self.cur.execute("CREATE TABLE IF NOT EXISTS data (%s);" % (', '.join(feature.name+' '+featureType(feature) for feature in self.features),))
        self.cur.execute("CREATE INDEX IF NOT EXISTS data_index ON data (%s);" % (', '.join(feature.name for feature in self.features),))
        self.conn.commit()
        
    def addData(self, *featureValues, **namedFeatureValues):
        data = super().addData(*featureValues, **namedFeatureValues)
        self.cur.execute('INSERT INTO data VALUES('+','.join(('?',)*len(data))+');', data)
        # self.conn.commit()

    def save(self):
        self.conn.commit()
        pass

    def load(self, noData=False):
        # ielādē tabulu atmiņā no sqlite datubāzes
        if not noData:
            rows = self.cur.execute('SELECT * FROM data;')
            for row in rows:
                self.data.append(row)

        for name in self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"):
            name = name[0]
            if name == 'data':
                continue
            category = SQLiteCategory(self, name)
            self.categories[name] = category
            if not noData:
                category.load()

        

    # privāti
    def open(self):
        pass

    def close(self):
        self.conn.close()
        pass



class SQLiteCategory(Category):

    def __init__(self, data, name):
        super().__init__(data, name)
        self.cur = self.data.conn.cursor()

    def reset(self):
        self.cur.execute("DROP INDEX IF EXISTS %s_index;" % (self.name,))
        self.cur.execute("DROP TABLE IF EXISTS '%s';" % (self.name,))
        self.data.conn.commit()

        self.cur.execute("CREATE TABLE IF NOT EXISTS '%s' (value INTEGER);" % (self.name,))
        self.cur.execute("CREATE INDEX IF NOT EXISTS %s_index ON '%s' (value);" % (self.name, self.name))
        self.data.conn.commit()

    def add(self, value):
        super().add(value)
        if value is not None:
            value = int(value)
        self.cur.execute("INSERT INTO '%s' VALUES(?);" % (self.name,), (value,))
        # self.data.conn.commit()

    def save(self):
        self.data.conn.commit()
        pass

    def load(self):
        # ielādē tabulu atmiņā no sqlite datubāzes
        rows = self.cur.execute("SELECT * FROM '%s';" % (self.name,))
        for row in rows:
            row = row[0]
            if row is not None:
                self.values.append(bool(row))
            else:
                self.values.append(row)


