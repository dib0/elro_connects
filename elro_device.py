class device:
    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, i):
        self.__id = i

    @property
    def device_type(self):
        return self.__device_type

    @device_type.setter
    def device_type(self, device_type):
        self.__device_type = device_type

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def device_state(self):
        return self.__device_state

    @device_state.setter
    def device_state(self, device_state):
        self.__device_state = device_state

    @property
    def battery_level(self):
        return self.__battery_level

    @battery_level.setter
    def battery_level(self, battery_level):
        self.__battery_level = battery_level
