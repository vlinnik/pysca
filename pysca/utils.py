from .bindable import Converter,Property

class LinearScale(Converter):
    def __init__(self):
        super().__init__( )
        self._rawLow = None
        self._rawHigh = None
        self._euLow = None
        self._euHigh = None
        self._decimals = 0

    def config(self, attr: dict = {}):
        try:
            for a in attr:
                setattr(self, a, attr[a])
        except AttributeError as e:
            pass

    def raw2eu(self, value: float,what: Property = None):
        if value is None:
            return value
        
        if what: self.config(what.properties)
        
        if self.rawLow is not None and value < self.rawLow:
            value = self.rawLow
        if self.rawHigh is not None and value > self.rawHigh:
            value = self.rawHigh
        if self.rawLow is None or self.rawHigh is None or self.rawLow == self.rawHigh:
            return value
        if self.euLow is not None and self.euHigh is not None and self.euLow != self.euHigh:
            value = (value - self.rawLow)/(self.rawHigh-self.rawLow)*(self.euHigh - self.euLow)+self.euLow
        
        return round(value,self._decimals)
    
    def eu2raw(self, value, what: Property = None):
        if value is None:
            return value
    
        if what: self.config(what.properties)
        
        if self.euLow is not None and value < self.euLow:
            value = self.euLow
        if self.euHigh is not None and value > self.euHigh:
            value = self.euHigh
        if self.euLow is None or self.euHigh is None or self.euLow == self.euHigh:
            return value
        if self.rawLow is not None and self.rawHigh is not None and self.rawLow != self.rawHigh:
            value = (value - self.euLow)/(self.euHigh-self.euLow)*(self.rawHigh - self.rawLow)+self.rawLow
        return value
    
    @property
    def euLow(self)->float:
        return self._euLow
    @euLow.setter
    def euLow(self,low:float):
        self._euLow = float(low)
    @property
    def euHigh(self)->float:
        return self._euHigh
    @euHigh.setter
    def euHigh(self,high:float):
        self._euHigh = float(high)
    @property
    def rawLow(self)->float:
        return self._rawLow
    @rawLow.setter
    def rawLow(self,low:float):
        self._rawLow = float(low)
    @property
    def rawHigh(self)->float:
        return self._rawHigh
    @rawHigh.setter
    def rawHigh(self,high:float):
        self._rawHigh = float(high)
    @property
    def decimals(self):
        return self._decimals
    @decimals.setter
    def decimals(self,decimals):
        self._decimals = decimals