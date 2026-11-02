# Initial commit: 10/14/2025 
# Last updated: 10/14/2025 

class Scenario:
    def __init__(self, filename):
        self.filename = filename
        self.scenario = []
        self.load_scenario()
    
    def load_scenario(self):
        with open(self.filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                self.scenario.append(list(line.strip()))
    
    def get_scenario(self):
        return self.scenario

def load_scenario(filename):
    return Scenario(filename)