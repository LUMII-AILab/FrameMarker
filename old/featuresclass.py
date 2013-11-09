#!/usr/bin/env python3

import inspect
from utils import Dict


class Features:

    def __init__(self, defaultDescription='discrete 1000000'):
        self.defaultDescription = defaultDescription
        self.features = []  # aka attributes
        self.NONE = "[NONE]"

    # izmantot kā dekorātoru (dekorētās funkcijas nosaukums pārtop par atribūta nosaukumu)
    def feature(self, *args, **kargs):

        description = self.defaultDescription

        def decorate(fn):
            name = fn.__name__  # šāda pieeja automātiski izslēdz nepieļaujamos simbolus nosaukumā, jo arī python nepieļauj līdzīgus simbolus
            argspec = inspect.getfullargspec(fn)
            self.features.append(Dict(name=name, extractor=fn, args=argspec.args, description=description))
            # print(self.attrs)
            # ja neko neatgriež, tad funkcijas nosaukums globāli satur None

        if len(args) == 1 and hasattr(args[0], '__call__') and not kargs:
            # izskatās, ka dekorātors ir izsaukts bez argumentiem, tātad bez iekavām
            decorate(args[0])
        else:
            if len(args) > 0 and type(args[0]) == str:
                description = args[0]
            return decorate
        # ja neko neatgriež, tad funkcijas nosaukums globālajā scopē satur None

    def __len__(self):
        return len(self.features)

    def __getitem__(self, index):
        return self.features[index]

    def __iter__(self):
        return iter(self.features)

    # extract features from token in sentence, potenciālie argumenti: token, tokens, ... u.c. tādi paši kā pazīmju extract funkcijām
    # rezultāts: Dict(feature1=..., feature2=..., ...)
    def __call__(self, *args, **kargs):

        output = Dict()

        for feature in self.features:

            # ja gadījumā uzdotie pozicionālie argumenti pārsniedz nepieciešamos, tad saīsina
            if len(args) > len(feature.args):
                args = args[:len(feature.args)]
                # print('Warning: too many arguments for feature', feature.name)

            # pārbauda, vai feature.args satur atslēgas, kuras nav kargs (padotas kā keyword argumenti) un neietilpst args (nav kā pozicionālie arg)
            # for key in set(feature.args) - kargs.keys():
            #     try:
            #         if feature.args.index(key) >= len(args):
            #             print('Error: no argument', key, 'specified')
            #             return
            #     except ValueError:
            #         pass

            # alternatīvs variants: vai args+kargs spēj nodrošināt nepieciešamos argumentus ?
            for key in feature.args[len(args):]:
                if key not in kargs:
                    print('Error: no argument', key, 'specified')
                    return


            output[feature.name] = feature.extractor(*args, **{key: kargs[key] for key in kargs.keys() & set(feature.args)})

        return output

    # TODO: pēc tam blackbox.put funkcija šo dictionary pārvērš par (feature1, feature2, ...)

