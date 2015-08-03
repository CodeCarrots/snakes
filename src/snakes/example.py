
WIDTH = 80
HEIGHT = 60

def get_example():
    with open('snakes/example.txt.py') as plik:
        return plik.read().format({
            'WIDTH': WIDTH,
            'HEIGHT': HEIGHT
        })
