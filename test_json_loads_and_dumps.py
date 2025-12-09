import json

#----------------------------------------------------------------------
# json.loads() convertrs json string to python dictionary
#----------------------------------------------------------------------
json_string = '{"name": "John", "age": 30, "city": "New York"}'
data = json.loads(json_string)

print(type(data))
print(data)

#----------------------------------------------------------------------
# json.dumps() convertrs python dictionary to json string
#----------------------------------------------------------------------
class Person:
  def __init__(self, name, age, city):
    self.name = name
    self.age = age
    self.city = city

person = Person(**data)
print(person.name, person.age, person.city)
print(json.dumps(person.__dict__))