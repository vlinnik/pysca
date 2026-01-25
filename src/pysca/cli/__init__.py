import csv  
from typing import Dict,Any,Union,List

def __auto_cast(value: str)->Union[str,int,float,None]:
    value = value.strip()

    # Пустые значения → None
    if value == "":
        return None

    # Попытка преобразовать в int
    try:
        return int(value)
    except ValueError:
        pass

    # Попытка преобразовать в float
    try:
        return float(value)
    except ValueError:
        pass

    # Иначе оставить строкой
    return value

def __args_parse(raw: str)->Dict[str,Any]:
    reader = csv.reader([raw]) 
    items = next(reader) 
    result = {} 
    for item in items: 
        key,value = item.split("=", 1) 
        result[key] = __auto_cast(value) 
    return result    

def args_parse(args: List[str])->Union[None,Dict[str,Any]]:
    if args:
        params = { }
        for arg in args:
            params.update(__args_parse(arg)) 
        return params 
    return None
