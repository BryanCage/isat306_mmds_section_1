class Menu(object):

    rootMin = 10  # Class Variable
    encodings = []

    def __init__(self, name, rootEncoding, menuList=None, mode=False):
        if(menuList == None):
            self._menuList = []
        else:
            self._menuList = menuList
        
        self._name = name
        self._knobMin = rootEncoding
        self._knobMax = len(menuList) + rootEncoding
        self._menuList = menuList
        self._mode = mode
        self._encodeList = {}
        self.toggleSwitch = False

        if(self._knobMin not in Menu.encodings and self._knobMax not in Menu.encodings):
            for i in range(self._knobMin, self._knobMax+1):
                Menu.encodings.append(i)
                Menu.encodings.sort()
            self._encoder = self._knobMin

        else:
            self._knobMin = max(Menu.encodings)+1
            self._knobMax = self._knobMin + len(menuList)
            for i in range(self._knobMin, self._knobMax+1):
                Menu.encodings.append(i)
                Menu.encodings.sort()
            self._encoder = self._knobMin

        for key in self._menuList:
            tempKey = key.strip()
            tempKey = key.replace(' ', '_')
            self._encodeList[tempKey] = self._menuList.index(
                key) + self._knobMin

    def menu(self, menu):
        for key in self._menuList:
            if(key == menu):
                self._menuList[key] = True
            else:
                self._menuList[key] = False
            print(self._menuList)

    def getMenuMode(self):
        return self._mode