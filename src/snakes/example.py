import os

WIDTH = 120
HEIGHT = 80

def get_example():
    p = os.path.join(os.path.dirname(__file__), 'example.txt.py')
    with open(p) as plik:
        data = plik.read()
        return data.format(**{
            'WIDTH': WIDTH,
            'HEIGHT': HEIGHT
        })
