class CurrentMenuRegistry(object):
    
    def __init__(self, menuRegistry=None):
        if(menuRegistry == None):
            self._menuRegistry = {}
        else:
            self._menuRegistry = menuRegistry
            
    def addMenuToRegister(self, menu):
        print(menu._mode)
        #self._menuRegistry[menu._mode] = False
        return self._menuRegistry
    def deleteMenuFromRegister(self, menu):
        del self._menuRegistry[menu]
        return self._menuRegistry
    
    
        