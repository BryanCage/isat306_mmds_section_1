class MenuRegistry(object):
    
    
    def __init__(self, menuRegistry=None):
        if(menuRegistry == None):
            self._menuRegistry = []
        else:
            self._menuRegistry = menuRegistry
            
    def addMenuToRegister(self, menu):

        if(menu in self._menuRegistry):
            print('Menu already in register.')
        else:
            menu._mode = False
            self._menuRegistry.append(menu)
        return self._menuRegistry
    
    def deleteMenuFromRegister(self, menu):
        if(menu in self._menuRegistry):
            del self._menuRegistry[self._menuRegistry.index(menu)]
        else:
            print('Menu was not found in register.')
        return self._menuRegistry
    
    def displayMenuRegistry(self):
        for menu in self._menuRegistry:
            print(menu._name)
            print('Current Mode: ' + str(menu._mode))
            print('Menu Items: ' + str(menu._menuList))
            print('Knob Min: ' + str(menu._knobMin))
            print('Knob Max: ' + str(menu._knobMax))
            print('Encodings: ' + str(menu._encodeList))
        
    def returnCurrentMenu(self):
        trueList = []
        falseList = []
        for menu in self._menuRegistry:
            if(menu._mode == True):
                trueList.append(menu)
                
            else:
                falseList.append(menu)
        print(trueList)
        print(falseList)
        if(len(trueList) > 1):
            print('Error: More than one menu mode True. Returning to "Main" menu.')
            for menu in self._menuRegistry:
                if(menu._name == "Main"):
                    self.setCurrentMenu(menu)
                    return menu
            return
##        if(len(tempList == 0)):
##           print('Error: no menu mode set to True')
        elif(len(trueList) == 0):
            print('Error: No menu mode set to True. Returning to "Main" menu.')
            for menu in self._menuRegistry:
                if(menu._name == "Main"):
                    self.setCurrentMenu(menu)
                    return menu
            return 
        else:
            exportMenu = trueList[0]
            return exportMenu
        
    def setCurrentMenu(self, selectedMenu):
        for menu in self._menuRegistry:
            if(selectedMenu == menu):
                selectedMenu._mode = True
            else:
                menu._mode = False
     