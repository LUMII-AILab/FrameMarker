#!/usr/bin/env python3

# JavaScript like dictionary: d.key <=> d[key]
# Elegants risinājums:
# http://stackoverflow.com/a/14620633
class Dict(dict):
    def __init__(self, *args, **kwargs):
        super(Dict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    # pagaidām nedarbojas uz pypy
    # ideja ir tāda: ja pieprasa neeksistējošu atslēgu, tad atgriež None
    # def __getitem(self, key):
    #     try:
    #         return super(Dict, self).__getitem__(key)
    #     except KeyError:
    #         return
    #     except:
    #         raise

    def __getattribute__(self, key):
        try:
            return super(Dict, self).__getattribute__(key)
        except:
            return

    def __delattr__(self, name):
        if name in self:
            del self[name]

