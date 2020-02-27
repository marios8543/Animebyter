from json import loads,load,dumps,dump

class JsonStore:
    def __init__(self,file):
        self.file = file
        try:
            self.dict = load(open(file,'r'))
        except:
            self.dict = {}

    def __getitem__(self,key):
        return self.dict[key]

    def __setitem__(self,key,value):
        self.dict[key] = value
        with open(self.file,'w') as f:
            dump(self.dict,f)