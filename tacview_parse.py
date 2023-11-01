from enum import Enum
class Record(Enum):
    Frame = 0
    Event = 1
    ReferenceTime = 2
    GlobalProperty = 3
    Update = 4
    Remove = 5


class Parser:
    def __init__(self, lines:list) -> None:
        self.ReferenceTime = None
        self.agent = dict()
        self.current_time = None
        self.lines = lines 

    def next(self):
        for num in range(len(self.lines)):
            record, value = parse_line(self.lines[num])
            match record:
                case Record.Frame:
                    self.current_time = value
                    yield self.current_time
                case Record.ReferenceTime:
                    self.ReferenceTime = value
                case Record.Update:
                    id, T_list, Name, Color = value
                    if id not in self.agent:
                        self.agent[id] = Agent()
                    self.agent[id].update(T_list, Name, Color)
                case Record.Remove:
                    self.agent.pop(value)
                case _:
                    pass

class Agent:
    def __init__(self) -> None:
        self.id = None
        self.Longitude = None
        self.Latitude  = None
        self.Altitude = None

        self.Roll = None
        self.Pitch = None
        self.Yaw = None

        self.U = None
        self.V = None
        self.Heading = None

        self.name = None
        self.color = None
    
    def update(self, T_list:list, Name, Color):
        T_list.reverse()
        self.Longitude = T_list.pop()
        self.Latitude  = T_list.pop()
        self.Altitude = T_list.pop()

        self.Roll = T_list.pop()
        self.Pitch = T_list.pop()
        self.Yaw = T_list.pop()

        self.name = Name
        self.color = Color


def parse_line(line: str):
    char = line[0] if line else None
    match char:
        case None:
            return None, None

        case '#':
            return Record.Frame, float(line[1:])

        case '0':
            name, value = line.split(',')[-1].split('=')
            return Record.ReferenceTime, (name, value)
        
        case '-':
            return Record.Remove, line[1:]
        
        case _:
            def parse_agent():
                value = line.split(',')
                value.reverse()

                id = value.pop()
                T_list = value.pop().split('=')[-1].split('|')
                Name = value.pop().split('=')[-1]
                Color = value.pop().split('=')[-1]
                return Record.Update, (id, T_list, Name, Color)
            try:
                return parse_agent()
            except:
                raise ValueError('Error: No conditions met!', line)
                print('Error:', line)
                return None, None
    
def safe_read(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
        lines = lines[2:]
        return lines

def main():
    filepath = r''    # Fill in the file path
    lines = safe_read(filepath)
    parser = Parser(lines)
    for deltatime in parser.next():
        print(deltatime)
        print(parser.agent)

main()