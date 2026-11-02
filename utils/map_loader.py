# Initial commit: 10/14/2025 
# Last updated: 10/14/2025 

class GridMap:
    def __init__(self, filename):
        self.filename = filename
        self.grid = []
        self.load_map()
    
    def load_map(self):
        with open(self.filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                self.grid.append(list(line.strip()))
    
    def get_grid(self):
        return self.grid

def load_map(filename):
    return GridMap(filename)
