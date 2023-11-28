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
        self.last_time = None
        self.current_time = None
        self.lines = lines 
        self.first_frame = True
        self.strid2intid = {}
        self.agent_dead_next_clean_list = []
        self.agent_dead_next_clean_flag = False

    def next(self):
        for num in range(len(self.lines)):
            record, value = parse_line(self.lines[num])
            match record:
                case Record.Frame:
                    self.last_time = self.current_time
                    self.current_time = value
                    if self.first_frame:
                        self.first_frame = False
                        continue
                    if self.agent_dead_next_clean_list and self.agent_dead_next_clean_flag:
                        [self.agent.pop(v) for v in self.agent_dead_next_clean_list]
                        self.agent_dead_next_clean_list = []
                        self.agent_dead_next_clean_flag = False
                    elif self.agent_dead_next_clean_list and not self.agent_dead_next_clean_flag:
                        self.agent_dead_next_clean_flag = True
                    yield self.last_time
                case Record.ReferenceTime:
                    self.ReferenceTime = value
                case Record.Update:
                    strid, T_list, Name, Color = value
                    if strid not in self.agent:
                        if strid not in self.strid2intid:
                            self.strid2intid[strid] = len(self.strid2intid) + 1
                        self.agent[strid] = Agent(self.strid2intid.get(strid))
                    self.agent[strid].update(T_list, Name, Color)
                case Record.Remove:
                    self.agent[value].state = 1
                    self.agent_dead_next_clean_list.append(value)
                case _:
                    pass

class Agent:
    def __init__(self, intid) -> None:
        self.intid = intid
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
        self.state = 0
        self.type = None
    
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
        self.camp = 0 if Color == "Red" else 1
        self.type = 0 if Name == "F16" else 1
    
    def attributes_to_str(self):
        return ' '.join([self.intid, self.Longitude, self.Latitude, self.Altitude, self.Roll, self.Pitch, self.Yaw, self.name, self.color])

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

# main()

